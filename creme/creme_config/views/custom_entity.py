################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from collections.abc import Sequence

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core import creme_jobs, models
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity, CremeUser, CustomEntityType
from creme.creme_core.utils import get_from_POST_or_404

from .. import bricks
from ..forms import custom_entity as ce_forms
from ..signals import disable_custom_entity_type
from . import base


class CustomEntityTypeCreation(base.ConfigCreation):
    form_class = ce_forms.CustomEntityTypeCreationForm
    title = _('New custom type of entity')
    submit_label = CustomEntityType.save_label

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)

        if not CustomEntityType.objects.filter(enabled=False).exists():
            raise ConflictError(
                gettext('You have reached the maximum number of custom types.')
            )


class CustomEntityTypeEdition(base.ConfigModelEdition):
    model = CustomEntityType
    form_class = ce_forms.CustomEntityTypeEditionForm
    pk_url_kwarg = 'cetype_id'

    def check_instance_permissions(self, instance, user):
        super().check_instance_permissions(instance=instance, user=user)
        if not instance.enabled:
            raise ConflictError(gettext('This custom type does not exist anymore.'))

        if instance.deleted:
            raise ConflictError(gettext(
                'This custom type cannot be edited because it is going to be deleted.'
            ))


class CustomEntityTypeRestoration(base.ConfigDeletion):
    ce_type_id_arg = 'id'

    @atomic
    def perform_deletion(self, request):
        ce_type = get_object_or_404(
            CustomEntityType.objects.filter(deleted=True),
            id=get_from_POST_or_404(request.POST, self.ce_type_id_arg)
        )

        ce_type.deleted = False
        ce_type.save()


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/custom-entity.html'
    brick_classes = [bricks.CustomEntitiesBrick]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['max_count'] = CustomEntityType.objects.count()

        return context


# Deletion ---------------------------------------------------------------------
@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_property_constraints',
)
def delete_customtype_ptypes_subject_ctypes(sender: CustomEntityType,
                                            entity_ctype: ContentType,
                                            **kwargs):
    entity_ctype.subject_ctypes_creme_property_set.clear()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_relation_constraints',
)
def delete_customtype_rtypes_subject_ctypes(sender: CustomEntityType,
                                            entity_ctype: ContentType,
                                            **kwargs):
    entity_ctype.relationtype_subjects_set.clear()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_role_m2m',
)
def delete_customtype_role_m2m(sender: CustomEntityType,
                               entity_ctype: ContentType,
                               **kwargs):
    entity_ctype.roles_allowing_creation.clear()
    entity_ctype.roles_allowing_export.clear()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_hfilters',
)
def delete_customtype_hfilters(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.HeaderFilter.objects.filter(entity_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_efilters',
)
def delete_customtype_efilters(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.EntityFilter.objects.filter(entity_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_cfields',
)
def delete_customtype_cfields(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.CustomField.objects.filter(content_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_workflows',
)
def delete_customtype_workflows(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.Workflow.objects.filter(content_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_buttons',
)
def delete_customtype_buttons(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.ButtonMenuItem.objects.filter(content_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_bricks',
)
def delete_customtype_bricks(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.BrickDetailviewLocation.objects.filter(content_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_history',
)
def delete_customtype_history(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.HistoryLine.objects.filter(entity_ctype=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_search',
)
def delete_customtype_search(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    models.SearchConfigItem.objects.filter(content_type=entity_ctype).delete()


@receiver(
    disable_custom_entity_type, dispatch_uid='creme_config-delete_customtype_jobs',
)
def delete_customtype_jobs(sender: CustomEntityType, entity_ctype: ContentType, **kwargs):
    for job in models.Job.objects.filter(type_id=creme_jobs.mass_import_type.id):
        # TODO: public API?
        if job.type._get_ctype(job.data) == entity_ctype:
            job.delete()

    model = sender.entity_model
    for job in models.Job.objects.filter(type_id=creme_jobs.batch_process_type.id):
        # TODO: public API?
        if job.type._get_model(job.data) == model:
            job.delete()


class CustomEntityTypeDeletion(base.ConfigDeletion):
    ce_type_id_arg = 'id'
    dependencies_limit = 3

    # TODO: factorise with CremeDeletionMixin.dependencies_to_html()
    @classmethod
    def dependencies_to_html(cls, *,
                             entities: Sequence[CremeEntity],
                             user: CremeUser,
                             ) -> str:
        def deps_generator():
            not_viewable_count = 0
            can_view = user.has_perm_to_view

            def entity_as_link(entity):
                return format_html(
                    '<a href="{url}" target="_blank"{deleted}>{label}</a>',
                    url=entity.get_absolute_url(),
                    deleted=(
                        mark_safe(' class="is_deleted"')
                        if entity.is_deleted else
                        ''
                    ),
                    label=entity,
                )

            # TODO: sort entities alphabetically?
            # TODO: priority to entity not deleted?
            for entity in entities:
                if can_view(entity):
                    yield entity_as_link(entity)
                else:
                    not_viewable_count += 1

            if not_viewable_count:
                yield ngettext(
                    '{count} not viewable entity',
                    '{count} not viewable entities',
                    not_viewable_count
                ).format(count=not_viewable_count)

        limit = cls.dependencies_limit

        # NB: we produce tuples for 'format_html_join()'
        def limited_items():
            for idx, item in enumerate(deps_generator()):
                if idx >= limit:
                    yield ('…',)
                    break

                yield (item,)

        return format_html(
            '<ul>{}</ul>',  # TODO: <class="...">?
            format_html_join('', '<li>{}</li>', limited_items())
        )

    @atomic
    def perform_deletion(self, request):
        ce_type = get_object_or_404(
            CustomEntityType.objects.filter(enabled=True),
            id=get_from_POST_or_404(request.POST, self.ce_type_id_arg),
        )

        model = ce_type.entity_model
        count = model.objects.count()
        if count:
            raise ConflictError(
                ngettext(
                    'This custom type cannot be deleted because {count} entity uses it.',
                    'This custom type cannot be deleted because {count} entities use it.',
                    count
                ).format(count=count)
            )

        # TODO: way to register models (non blocking entity models, blocking models)?
        # We cannot be sure we can delete entities in signal handler (e.g. internal
        # relationships could block the deletion). So, in this first version we
        # raise an error if an entity is referencing teh ContentType.
        content_type = ContentType.objects.get_for_model(model)
        # NB: 'creme_registry.iter_entity_models()' does not return all entity
        #     models, but is it OK?
        for entity_model in apps.get_models():
            if not issubclass(entity_model, CremeEntity):
                continue

            for field in entity_model._meta.fields:
                fname = field.name

                # Not entity with this type should exist, we avoid queries
                if fname == 'entity_type':
                    continue

                if field.is_relation and field.related_model == ContentType:
                    dependencies = entity_model.objects.filter(**{fname: content_type})[:100]
                    if dependencies:
                        raise ConflictError(
                            '<span>{message}</span>{dependencies}'.format(
                                message=gettext(
                                    'This custom type cannot be deleted because of its links '
                                    'with some entities:'
                                ),
                                dependencies=self.dependencies_to_html(
                                    entities=dependencies, user=request.user,
                                ),
                            )
                        )

        if ce_type.deleted:
            ce_type.deleted = False
            ce_type.enabled = False

            disable_custom_entity_type.send_robust(
                sender=ce_type,
                entity_ctype=ContentType.objects.get_for_model(model),
            )
        else:
            ce_type.deleted = True

        ce_type.save()
