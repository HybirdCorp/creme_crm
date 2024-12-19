################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme.creme_core import models
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CustomEntityType
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


class CustomEntityRestoration(base.ConfigDeletion):
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


class CustomEntityDeletion(base.ConfigDeletion):
    ce_type_id_arg = 'id'

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
