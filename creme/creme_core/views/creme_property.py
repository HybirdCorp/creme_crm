################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging

from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.http import Http404
from django.shortcuts import get_list_or_404, get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

# TODO: move them to creme_core ?
import creme.creme_config.forms.creme_property_type as ptype_forms

from ..auth import EntityCredentials
from ..core.entity_filter.condition_handler import PropertyConditionHandler
from ..core.exceptions import ConflictError
from ..core.paginator import FlowPaginator
from ..forms import creme_property as prop_forms
from ..gui.bricks import ForbiddenBrick, QuerysetBrick, SimpleBrick
from ..models import (
    CremeEntity,
    CremeProperty,
    CremePropertyType,
    EntityFilter,
    Workflow,
)
from ..models.utils import model_verbose_name_plural
from ..utils import get_from_POST_or_404
from ..utils.content_type import entity_ctypes
from ..utils.html import render_limited_list
from ..workflows import PropertyAddingTrigger
from . import generic
from .bricks import BricksReloading
from .generic.base import EntityCTypeRelatedMixin

# TODO: Factorise with views in creme_config

logger = logging.getLogger(__name__)


# TODO: Factorise with add_relations_bulk and bulk_update?
class PropertiesBulkAdding(EntityCTypeRelatedMixin,
                           generic.CremeFormPopup):
    form_class = prop_forms.PropertiesBulkAddingForm
    title = _('Multiple adding of properties')
    submit_label = _('Add the properties')

    def filter_entities(self, entities):
        filtered = {True: [], False: []}
        has_perm = self.request.user.has_perm_to_change

        for entity in entities:
            filtered[has_perm(entity)].append(entity)

        return filtered

    def get_entities(self, model):
        request = self.request
        entities = get_list_or_404(
            model,
            pk__in=(
                request.POST.getlist('ids')
                if request.method == 'POST' else
                request.GET.getlist('ids')
            ),
        )

        CremeEntity.populate_real_entities(entities)

        return entities

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        model = self.get_ctype().model_class()
        kwargs['model'] = model

        filtered = self.filter_entities(self.get_entities(model=model))
        kwargs['entities'] = filtered[True]
        kwargs['forbidden_entities'] = filtered[False]

        return kwargs


class PropertiesAdding(generic.RelatedToEntityFormPopup):
    form_class = prop_forms.PropertiesAddingForm
    title = _('New properties for «{entity}»')
    submit_label = _('Add the properties')


class PropertyTypeCreation(generic.CremeModelCreation):
    model = CremePropertyType
    form_class = ptype_forms.CremePropertyForm
    permissions = 'creme_core.can_admin'


class PropertyTypeEdition(generic.CremeModelEdition):
    # model = CremePropertyType
    queryset = CremePropertyType.objects.filter(is_custom=True, enabled=True)
    form_class = ptype_forms.CremePropertyForm
    pk_url_kwarg = 'ptype_id'
    permissions = 'creme_core.can_admin'


class PropertyFromFieldsDeletion(generic.base.EntityRelatedMixin,
                                 generic.CremeModelDeletion):
    model = CremeProperty

    entity_id_arg = 'entity_id'
    ptype_id_arg = 'ptype_id'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.property_type = None

    def get_query_kwargs(self):
        return {
            'type':            self.get_property_type(),
            'creme_entity_id': self.get_related_entity().id,
        }

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.entity_id_arg)

    def get_property_type(self):
        ptype = self.property_type

        if ptype is None:
            self.property_type = ptype = get_object_or_404(
                CremePropertyType, id=self.get_property_type_id(),
            )

        return ptype

    def get_property_type_id(self):
        return get_from_POST_or_404(self.request.POST, self.ptype_id_arg)

    def get_success_url(self):
        # TODO: callback_url?
        return self.get_property_type().get_absolute_url()


class CTypePropertiesDeletion(generic.base.EntityCTypeRelatedMixin,
                              generic.CremeDeletion):
    ptype_id_arg = 'ptype_id'
    ctype_id_arg: str = 'ct_id'

    def get_ctype_id(self) -> int:
        return get_from_POST_or_404(self.request.POST, key=self.ctype_id_arg, cast=int)

    def get_ptype_id(self) -> int:
        return get_from_POST_or_404(self.request.POST, key=self.ptype_id_arg, cast=int)

    def get_success_url(self):
        return reverse('creme_core__ptype', args=(self.get_ptype_id(),))

    def perform_deletion(self, request):
        ctype = self.get_ctype()
        ptype_id = self.get_ptype_id()

        key = 'cremeentity_ptr_id'
        # NB: CremeUser.has_perm_to_change() returns False for deleted entities,
        #     but EntityCredentials.filter(perm=EntityCredentials.CHANGE, ...)
        #     does not exclude them => is this a problem??
        qs = EntityCredentials.filter(
            user=self.request.user,
            queryset=ctype.model_class()
                          .objects
                          .order_by(key)
                          .filter(properties__type=ptype_id, is_deleted=False),
            perm=EntityCredentials.CHANGE,
        )
        for page in FlowPaginator(
            queryset=qs,
            key=key,
            per_page=256,
            count=qs.count(),
        ).pages():
            with atomic():
                CremeProperty.objects.filter(
                    type_id=ptype_id,
                    creme_entity_id__in=[e.id for e in page.object_list],
                ).delete()


class PropertyTypeDeletion(generic.CremeModelDeletion):
    model = CremePropertyType
    permissions = 'creme_core.can_admin'

    ptype_id_url_kwarg = 'ptype_id'

    # TODO: do we need a "weak reference" (M2M, id/uuid stored in JSON...) system?
    # TODO: split in several methods?
    def check_instance_permissions(self, instance, user):
        rtypes = [
            *instance.relationtype_subjects_set.all(),
            *instance.relationtype_forbidden_set.all(),
        ]
        if rtypes:
            raise ConflictError(
                gettext(
                    'The property type cannot be deleted because it is used as '
                    'relationship type constraint in: {rtypes}'
                ).format(
                    # TODO: add a detail view for relation type, then render a link
                    rtypes=', '.join(f'«{rtype.predicate}»' for rtype in rtypes),
                )
            )

        # ---
        efilters = EntityFilter.objects.filter(
            conditions__type=PropertyConditionHandler.type_id,
            conditions__name=instance.uuid,
        )
        if efilters:
            def efilter_to_link(efilter):
                url = efilter.get_absolute_url()

                return format_html(
                    '<a href="{url}" target="_blank">{label}</a>',
                    url=url, label=efilter,
                ) if url else f'{efilter.name} *{efilter.registry.verbose_name}*'

            raise ConflictError(
                _(
                    'The property type cannot be deleted because it is used in '
                    'filter conditions: {filters}'
                ).format(
                    filters=render_limited_list(
                        items=efilters,
                        limit=self.dependencies_limit,
                        render_item=efilter_to_link,
                    ),
                )
            )

        # ---
        workflows = [
            workflow
            for workflow in Workflow.objects.all()
            if isinstance(workflow.trigger, PropertyAddingTrigger)
            and workflow.trigger.property_type == instance
        ]
        if workflows:
            raise ConflictError(
                gettext(
                    'The property type cannot be deleted because it is used by '
                    'triggers of Workflow: {workflows}'
                ).format(
                    # TODO: add a detail view for workflows, then render a link?
                    workflows=', '.join(f'«{wf}»' for wf in workflows),
                )
            )

        # TODO: uncomment when conditions on properties are managed by Workflow
        # ptype_uuid = str(instance.uuid)
        # workflows = [
        #     workflow
        #     for workflow in Workflow.objects.all()
        #     # todo: add an API for '_conditions_per_source'
        #     for source_conditions in workflow.conditions._conditions_per_source
        #     for condition in source_conditions['conditions']
        #     if condition.type == PropertyConditionHandler.type_id
        #     and condition.name == ptype_uuid
        # ]
        # if workflows:
        #     raise ConflictError(
        #         gettext(
        #             'The property type cannot be deleted because it is used by '
        #             'conditions of Workflow in: {workflows}'
        #         ).format(
        #             # todo: add a detail view for workflows, then render a link?
        #             workflows=', '.join(f'«{wf}»' for wf in workflows),
        #         )
        #     )

        # NB: we currently do not check HeaderFilters/CustomBrickConfigItems/
        #     RelationBrickItems; they are just for UI (& not business logic) so,
        #     it's probably OK that they do not block the deletion.
        #     It could change in the future of course depending on feedbacks.

    def get_query_kwargs(self):
        return {
            'id': self.kwargs[self.ptype_id_url_kwarg],
            'is_custom': True,
        }

    def get_ajax_success_url(self):
        # TODO: callback_url?
        return self.object.get_lv_absolute_url()

    def get_success_url(self):
        # TODO: callback_url?
        return self.object.get_lv_absolute_url()


class PropertyTypeBarHatBrick(SimpleBrick):
    id = 'property_hat_bar'
    dependencies = '*'
    template_name = 'creme_core/bricks/ptype-hat-bar.html'


class PropertyTypeInfoBrick(SimpleBrick):
    id = 'property_type_info'
    dependencies = '*'
    read_only = True
    template_name = 'creme_core/bricks/ptype-info.html'


class TaggedEntitiesBrick(QuerysetBrick):
    template_name = 'creme_core/bricks/tagged-entities.html'

    id_prefix = 'tagged'

    def __init__(self, ctype):
        super().__init__()
        self.ctype = ctype
        self.id = f'{self.id_prefix}-{ctype.app_label}-{ctype.model}'
        self.dependencies = (ctype.model_class(),)

    @classmethod
    def parse_brick_id(cls, brick_id) -> ContentType | None:
        """Extract info from brick ID.

        @param brick_id: e.g. "tagged-persons-contact".
        @return A ContentType instance if valid, else None.
        """
        parts = brick_id.split('-')

        if len(parts) != 3:
            logger.warning('parse_brick_id(): the brick ID "%s" has a bad length', brick_id)
            return None

        if parts[0] != cls.id_prefix:
            logger.warning('parse_brick_id(): the brick ID "%s" has a bad prefix', brick_id)
            return None

        try:
            ctype = ContentType.objects.get_by_natural_key(parts[1], parts[2])
        except ContentType.DoesNotExist:
            logger.warning(
                'parse_brick_id(): the brick ID "%s" has an invalid ContentType key',
                brick_id,
            )
            return None

        if not issubclass(ctype.model_class(), CremeEntity):
            logger.warning(
                'parse_brick_id(): the brick ID "%s" is not related to CremeEntity',
                brick_id,
            )
            return None

        return ctype

    def detailview_display(self, context):
        ctype = self.ctype

        return self._render(self.get_template_context(
            context,
            ctype.get_all_objects_for_this_type(properties__type=context['object']),
            ctype=ctype,  # If the model is inserted in the context,
                          #  the template call it and create an instance...
        ))


class TaggedMiscEntitiesBrick(QuerysetBrick):
    id = 'misc_tagged_entities'
    dependencies = (CremeEntity,)
    template_name = 'creme_core/bricks/tagged-entities.html'

    def __init__(self, excluded_ctypes):
        super().__init__()
        self.excluded_ctypes = excluded_ctypes

    def detailview_display(self, context):
        btc = self.get_template_context(
            context,
            CremeEntity.objects.filter(properties__type=context['object'])
                               .exclude(entity_type__in=self.excluded_ctypes),
            ctype=None,
        )

        CremeEntity.populate_real_entities(btc['page'].object_list)

        return self._render(btc)


class PropertyTypeDetail(generic.CremeModelDetail):
    model = CremePropertyType
    queryset = CremePropertyType.objects.prefetch_related('subject_ctypes')
    template_name = 'creme_core/detail/property-type.html'
    pk_url_kwarg = 'ptype_id'
    bricks_reload_url_name = 'creme_core__reload_ptype_bricks'

    def get_bricks(self):
        ptype = self.object
        ctypes = ptype.subject_ctypes.all()
        main_bricks = [PropertyTypeInfoBrick()]
        user = self.request.user

        if ctypes:
            has_perm_to_access = user.has_perm_to_access

            for ctype in ctypes:
                brick = TaggedEntitiesBrick(ctype=ctype)
                if not has_perm_to_access(ctype.app_label):
                    brick = ForbiddenBrick(
                        id=brick.id,
                        verbose_name=model_verbose_name_plural(ctype.model_class()),
                    )

                main_bricks.append(brick)

            main_bricks.append(TaggedMiscEntitiesBrick(excluded_ctypes=ctypes))
        else:
            main_bricks.extend(
                TaggedEntitiesBrick(ctype=ctype)
                for ctype in entity_ctypes(
                    app_labels=None if user.is_superuser else user.role.allowed_apps,
                )
            )

        return {
            'hat': [PropertyTypeBarHatBrick()],
            'main': main_bricks,
        }

    def get_bricks_reload_url(self):
        return reverse(self.bricks_reload_url_name, args=(self.object.id,))


class PropertyTypeBricksReloading(BricksReloading):
    ptype_id_url_kwarg = 'ptype_id'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ptype = None

    def get_bricks(self):
        ptype = self.get_property_type()
        bricks = []
        ctypes = ptype.subject_ctypes.all()

        for brick_id in self.get_brick_ids():
            match brick_id:
                case PropertyTypeBarHatBrick.id:
                    brick = PropertyTypeBarHatBrick()
                case PropertyTypeInfoBrick.id:
                    brick = PropertyTypeInfoBrick()
                case TaggedMiscEntitiesBrick.id:
                    brick = TaggedMiscEntitiesBrick(excluded_ctypes=ctypes)
                case _:
                    ctype = TaggedEntitiesBrick.parse_brick_id(brick_id)
                    if ctype is None:
                        raise Http404(f'Invalid brick id "{brick_id}"')

                    brick = TaggedEntitiesBrick(ctype=ctype)

                    # TODO: factorise
                    if not self.request.user.has_perm_to_access(ctype.app_label):
                        brick = ForbiddenBrick(
                            id=brick.id,
                            # verbose_name=ctype.model_class()._meta.verbose_name_plural,
                            verbose_name=model_verbose_name_plural(ctype.model_class()),
                        )

            bricks.append(brick)

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['object'] = self.get_property_type()

        return context

    def get_property_type(self):
        ptype = self.ptype

        if ptype is None:
            self.ptype = ptype = get_object_or_404(
                CremePropertyType.objects.prefetch_related('subject_ctypes'),
                id=self.kwargs[self.ptype_id_url_kwarg],
            )

        return ptype
