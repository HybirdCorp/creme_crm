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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import Field
from django.db.models.deletion import PROTECT
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import partition
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext, pgettext_lazy

from .. import utils
from ..auth.decorators import login_required
from ..core.entity_filter import EF_REGULAR, entity_filter_registries
from ..core.exceptions import BadRequestError, ConflictError
from ..enumerators import UserEnumerator
from ..forms.entity_filter import forms as efilter_forms
from ..gui import bricks
from ..gui.listview import ListViewState
from ..http import CremeJsonResponse
from ..models import CremeEntity, EntityFilter, RelationType
from ..utils import db as db_utils
from ..utils.content_type import entity_ctypes
from ..utils.unicode_collation import collator
from . import generic
from .bricks import BricksReloading
from .decorators import jsonify
from .enumerable import FieldChoicesView
from .generic import base

logger = logging.getLogger(__name__)
User = get_user_model()


class FilterMixin:
    """Code factorisation with HeaderFilter views."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lv_url = None

    def build_lv_url(self):
        url = self.lv_url

        if url is None:
            url = self.request.POST.get('cancel_url')

            if not url:
                model = self.object.entity_type.model_class()

                try:
                    url = model.get_lv_absolute_url()
                except AttributeError:
                    logger.debug('"%s" has no get_lv_absolute_url() method ?!', model)
                    url = ''

            self.lv_url = url

        return url

    def check_filter_permissions(self, filter_obj, user):
        allowed, msg = filter_obj.can_edit(user)

        if not allowed:
            raise PermissionDenied(msg)

    @staticmethod
    def get_case_sensitivity_message():
        if not db_utils.is_db_equal_case_sensitive():
            if not db_utils.is_db_like_case_sensitive():
                return _(
                    'Notice: your database is not case-sensitive, so the string '
                    'operators which are case-sensitive and the ones which are '
                    'not will accept the same entities.'
                )

            return _(
                'Notice: your database is not case-sensitive for the "equals" '
                'operator, so the string equality operators which are '
                'case-sensitive and the ones which are not will accept the same entities.'
            )
        elif not db_utils.is_db_like_case_sensitive():
            return _(
                'Notice: your database is not case-sensitive, so the string operators '
                'which are case-sensitive and the ones which are not will accept '
                'the same entities (excepted equality ones, which are case-sensitive).'
            )

        return None

    # TODO: rename (shadows view method)
    def get_success_url(self):
        # TODO: callback_url?
        return self.build_lv_url() or reverse('creme_core__home')

    def save_in_session(self, lvs_attr):
        request = self.request
        lv_url = self.build_lv_url()
        lvs = ListViewState.get_state(request, lv_url) or ListViewState(url=lv_url)

        setattr(lvs, lvs_attr, self.object.id)
        lvs.register_in_session(request)


class EntityFilterMixin(FilterMixin):
    efilter_registries = entity_filter_registries
    efilter_type: str = EF_REGULAR

    def get_efilter_registry(self):
        return self.efilter_registries[self.efilter_type]


class EntityFilterBarHatBrick(bricks.SimpleBrick):
    id = 'efilter_hat_bar'
    dependencies = [EntityFilter]
    template_name = 'creme_core/bricks/efilter-hat-bar.html'

    def _get_edition_info(self, user, efilter):
        edition_allowed, edition_error = efilter.can_edit(user)
        edition_info = {
            'url': efilter.get_edit_absolute_url(),
            'allowed': edition_allowed,
        }
        if not edition_allowed:
            edition_info['error'] = edition_error

        return edition_info

    def _get_deletion_info(self, user, efilter):
        deletion_allowed, deletion_error = efilter.can_delete(user)
        deletion_info = {
            'url': efilter.get_delete_absolute_url(),
            'allowed': deletion_allowed,
        }
        if not deletion_allowed:
            deletion_info['error'] = deletion_error

        return deletion_info

    def get_template_context(self, context, **extra_kwargs):
        efilter = context['object']
        user = context['user']

        return super().get_template_context(
            context,
            edition=self._get_edition_info(user=user, efilter=efilter),
            deletion=self._get_deletion_info(user=user, efilter=efilter),
            **extra_kwargs
        )


class EntityFilterInfoBrick(bricks.SimpleBrick):
    id = 'efilter_info'
    read_only = True
    template_name = 'creme_core/bricks/efilter-info.html'


class EntityFilterParentsBrick(bricks.PaginatedBrick):
    id = 'efilter_parents'
    read_only = True
    template_name = 'creme_core/bricks/efilter-parents.html'

    def detailview_display(self, context):
        efilter = context['object']

        return self._render(self.get_template_context(
            context,
            # NB: we retrieve all parent; it should not be a big issue because
            #     you're not supposed to have hundreds of filters.
            [cond.filter for cond in efilter._iter_parent_conditions()],
        ))


class EntityFilterLinkedEntitiesBrick(bricks.QuerysetBrick):
    read_only = True
    template_name = 'creme_core/bricks/efilter-linked-entities.html'

    id_prefix = 'linked_to_efilter'

    def __init__(self, model, field):
        super().__init__()
        self.model = model
        self.field = field
        self.id = (
            f'{self.id_prefix}-{model._meta.app_label}-{model.__name__.lower()}-{field.name}'
        )
        self.dependencies = (model,)

    @classmethod
    def parse_brick_id(cls, brick_id: str) -> tuple[type[CremeEntity], Field] | None:
        """Extract info from brick ID.

        @param brick_id: e.g. "linked_to_efilter-reports-report-filter".
        @return: A tuple with the concerned model & field; or None if an error occurred.
        """
        parts = brick_id.split('-')

        if len(parts) != 4:
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

        model = ctype.model_class()
        if not issubclass(model, CremeEntity):
            logger.warning(
                'parse_brick_id(): the brick ID "%s" is not related to CremeEntity',
                brick_id,
            )
            return None

        try:
            field = model._meta.get_field(parts[3])
        except FieldDoesNotExist:
            logger.warning(
                'parse_brick_id(): the brick ID "%s" has an invalid field name',
                brick_id,
            )
            return None

        if not field.many_to_one or field.remote_field.model != EntityFilter:
            logger.warning(
                'parse_brick_id(): the brick ID "%s" has an invalid field type',
                brick_id,
            )
            return None

        return (model, field)

    def detailview_display(self, context):
        field = self.field

        # TODO?
        #  if not context['user'].has_perm_to_access(self.model._meta.app_label):
        #     message = ...

        return self._render(self.get_template_context(
            context,
            self.model.objects.filter(**{field.name: context['object']}),
            field=field,
            # TODO: unit test case with False
            protected=(field.remote_field.on_delete == PROTECT),
        ))


class EntityFilterDetail(EntityFilterMixin, generic.CremeModelDetail):
    model = EntityFilter
    template_name = 'creme_core/detail/entity-filter.html'
    pk_url_kwarg = 'efilter_id'
    bricks_reload_url_name = 'creme_core__reload_efilter_bricks'

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)
        if instance.filter_type != self.efilter_type:
            raise ConflictError('You cannot view this type of filter thought this URL')

        allowed, msg = instance.can_view(user)
        if not allowed:
            raise PermissionDenied(msg)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #
    #     efilter = self.object
    #     user = self.request.user
    #     context['edition_perm'] = efilter.can_edit(user)[0]
    #     context['deletion_perm'] = efilter.can_delete(user)[0]
    #
    #     return context

    # def get_bricks(self):
    #     bricks = [EntityFilterInfoBrick(), EntityFilterParentsBrick()]
    #     efilter = self.object
    #
    #     for rel_objects in (f for f in efilter._meta.get_fields() if f.one_to_many):
    #         if issubclass(rel_objects.related_model, CremeEntity):
    #             bricks.append(
    #                 EntityFilterLinkedEntitiesBrick(
    #                     model=rel_objects.related_model,
    #                     field=rel_objects.field,
    #                 )
    #             )
    #     return bricks
    def get_bricks(self):
        main_bricks = [EntityFilterInfoBrick(), EntityFilterParentsBrick()]
        efilter = self.object

        # TODO: regroup fields from the same model?
        #   => how to indicate PROTECT FKs which will stop deletion
        #   => what about non-viewable fields?
        for rel_objects in (f for f in efilter._meta.get_fields() if f.one_to_many):
            if issubclass(rel_objects.related_model, CremeEntity):
                main_bricks.append(
                    EntityFilterLinkedEntitiesBrick(
                        model=rel_objects.related_model,
                        field=rel_objects.field,
                    )
                )

        # TODO: manage ManyToMany too
        #     for rel_objects in (
        #         f
        #         for f in efilter._meta.get_fields(include_hidden=True)
        #         if f.many_to_many and f.auto_created
        #     ): [...]

        return {
            'hat': [EntityFilterBarHatBrick()],
            'main': main_bricks,
        }

    def get_bricks_reload_url(self):
        return reverse(self.bricks_reload_url_name, args=(self.object.id,))


class EntityFilterBricksReloading(BricksReloading):
    efilter_id_url_kwarg = 'efilter_id'
    filter_type = EF_REGULAR

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.efilter = None

    def check_instance_permissions(self, instance, user):
        allowed, msg = instance.can_view(user)
        if not allowed:
            raise PermissionDenied(msg)

    def get_bricks(self):
        bricks = []

        for brick_id in self.get_brick_ids():
            # NB: not useful
            # if brick_id == EntityFilterBarHatBrick.id:
            #     brick = EntityFilterBarHatBrick()
            # elif brick_id == EntityFilterInfoBrick.id:
            #     brick = EntityFilterInfoBrick()

            if brick_id == EntityFilterParentsBrick.id:
                brick = EntityFilterParentsBrick()
            else:
                model_n_field = EntityFilterLinkedEntitiesBrick.parse_brick_id(brick_id)
                if model_n_field is None:
                    raise Http404(f'Invalid brick id "{brick_id}"')

                brick = EntityFilterLinkedEntitiesBrick(
                    model=model_n_field[0], field=model_n_field[1],
                )

            bricks.append(brick)

        return bricks

    def get_bricks_context(self):
        context = super().get_bricks_context()
        context['object'] = self.get_efilter()

        return context

    def get_efilter(self):
        efilter = self.efilter

        if efilter is None:
            efilter = get_object_or_404(
                EntityFilter,
                id=self.kwargs[self.efilter_id_url_kwarg],
                filter_type=self.filter_type,
            )
            self.check_instance_permissions(instance=efilter, user=self.request.user)

            self.efilter = efilter

        return efilter


class EntityFilterCreation(base.EntityCTypeRelatedMixin,
                           EntityFilterMixin,
                           generic.CremeModelCreation):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterCreationForm
    template_name = 'creme_core/forms/entity-filter.html'
    ctype_form_kwarg = 'ctype'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('entity_filter_id')

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = self.get_case_sensitivity_message()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.ctype_form_kwarg] = self.get_ctype()
        kwargs['efilter_registry'] = self.get_efilter_registry()

        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['is_private'] = settings.FILTERS_INITIAL_PRIVATE

        return initial


class EntityFilterCloning(EntityFilterMixin, generic.CremeModelCreation):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterCloningForm
    template_name = 'creme_core/forms/entity-filter.html'
    pk_url_kwarg = 'efilter_id'
    source_form_kwarg = 'source'

    def get_source(self):
        efilter = get_object_or_404(EntityFilter, pk=self.kwargs[self.pk_url_kwarg])
        self.request.user.has_perm_to_access_or_die(efilter.entity_type.app_label)

        return efilter

    def form_valid(self, form):
        response = super().form_valid(form)
        self.save_in_session('entity_filter_id')

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = self.get_case_sensitivity_message()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs[self.source_form_kwarg] = self.get_source()
        kwargs['efilter_registry'] = self.get_efilter_registry()

        return kwargs

    # TODO?
    # def get_initial(self):
    #     initial = super().get_initial()
    #     initial['is_private'] = settings.FILTERS_INITIAL_PRIVATE
    #
    #     return initial


class EntityFilterEdition(EntityFilterMixin, generic.CremeModelEdition):
    model = EntityFilter
    form_class = efilter_forms.EntityFilterEditionForm
    template_name = 'creme_core/forms/entity-filter.html'
    pk_url_kwarg = 'efilter_id'
    submit_label = _('Save the modified filter')

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)
        if instance.filter_type != self.efilter_type:
            raise ConflictError('You cannot edit this type of filter thought this URL')

        self.check_filter_permissions(filter_obj=instance, user=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['help_message'] = self.get_case_sensitivity_message()

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['efilter_registry'] = self.get_efilter_registry()

        return kwargs


class EntityFilterDeletion(EntityFilterMixin,
                           base.CallbackMixin,
                           generic.CremeModelDeletion):
    model = EntityFilter
    pk_url_kwarg = 'efilter_id'

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)
        if instance.filter_type != self.efilter_type:
            raise ConflictError('You cannot delete this type of filter thought this URL')

        allowed, msg = instance.can_delete(user)
        if not allowed:
            raise PermissionDenied(msg)

    def get_query_kwargs(self):
        return {'pk': self.kwargs[self.pk_url_kwarg]}

    def _get_success_url(self):
        return (
            self.get_callback_url()
            or self.object.entity_type.model_class().get_lv_absolute_url()
        )

    def get_ajax_success_url(self):
        return self._get_success_url()

    def get_success_url(self):
        return self._get_success_url()

    def perform_deletion(self, request):
        try:
            super().perform_deletion(request)
        except EntityFilter.DependenciesError as e:
            raise ConflictError(e) from e


# TODO: factorise with views.relations.json_rtype_ctypes  ???
@login_required
@jsonify
def get_content_types(request, rtype_id):
    content_types = get_object_or_404(
        RelationType, pk=rtype_id,
    ).object_ctypes.all() or entity_ctypes()

    return [
        (0, pgettext('creme_core-filter', 'All')),
        *((ct.id, str(ct)) for ct in content_types),
    ]


class EntityFilterChoices(base.ContentTypeRelatedMixin, base.CheckedView):
    response_class = CremeJsonResponse
    ctype_id_arg = 'ct_id'
    efilter_types_arg = 'type'
    include_all_arg = 'all'
    all_label = pgettext_lazy('creme_core-filter', 'All')

    def check_related_ctype(self, ctype):
        self.request.user.has_perm_to_access_or_die(ctype.app_label)

    def get_ctype_id(self):
        return utils.get_from_GET_or_404(self.request.GET, self.ctype_id_arg, int)

    def get_efilter_types(self) -> list[str]:
        efilter_types = self.request.GET.getlist(self.efilter_types_arg)

        if efilter_types:
            for filter_type in efilter_types:
                try:
                    entity_filter_registries[filter_type]
                except KeyError as e:
                    raise Http404(f'Invalid type of filter "{filter_type}"') from e
        else:
            efilter_types = [EF_REGULAR]

        return efilter_types

    def get_include_all(self):
        return utils.get_from_GET_or_404(
            self.request.GET,
            key=self.include_all_arg,
            cast=utils.bool_from_str_extended,
            default='0',
        )

    def get_choices(self):
        choices = [('', self.all_label)] if self.get_include_all() else []
        choices.extend(
            (efilter.id, str(efilter))
            for efilter in EntityFilter.objects.filter_by_user(
                self.request.user, types=self.get_efilter_types(),
            ).filter(entity_type=self.get_ctype())
        )

        return choices

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_choices(),
            safe=False,  # Result is not a dictionary
        )


class EntityFilterUserEnumerator(UserEnumerator):
    def __init__(
        self,
        field: Field,
        filter_type=EF_REGULAR,
        search_fields=None,
        limit_choices_to=None
    ):
        self.efilter_registry = self.get_efilter_registry(filter_type)
        super().__init__(field, search_fields, limit_choices_to)

    def get_efilter_registry(self, filter_type):
        try:
            return entity_filter_registries[filter_type]
        except KeyError:
            raise BadRequestError(f'Unknown entity filter type {filter_type}')

    def get_user_operands(self, user):
        for operand in self.efilter_registry.operands(user):
            if issubclass(operand.model, User):
                yield operand

    # TODO: unit test
    def to_python(self, user, values):
        operands = {o.type_id for o in self.get_user_operands(user)}

        op_ids, pks = partition(lambda v: v in operands, values)
        return [*op_ids, *self._queryset(user).filter(pk__in=pks)]

    def choices(self, user, *, term=None, only=None, limit=None):
        sort_key = collator.sort_key
        choices = [
            {
                'value': op.type_id,
                'label': op.verbose_name,
            } for op in self.get_user_operands(user)
        ]
        choices.sort(key=lambda d: sort_key(d['label']))

        choices.extend(
            super().choices(user, term=term, only=only)
        )

        return choices[:limit] if limit else choices


class UserChoicesView(FieldChoicesView):
    filter_type_arg = 'filter_type'

    def get_enumerator(self):
        model = self.get_ctype().model_class()
        field_name = self.get_field_name()

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            raise Http404('This field does not exist.') from e

        return EntityFilterUserEnumerator(field, filter_type=self.filter_type)

    def get(self, request, *args, **kwargs):
        # TODO: check type?
        self.filter_type = request.GET.get('filter_type', EF_REGULAR)

        return super().get(request, *args, **kwargs)
