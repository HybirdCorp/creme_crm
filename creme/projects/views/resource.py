# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Relation
from creme.creme_core.views import generic

from .. import get_task_model
from ..constants import REL_SUB_PART_AS_RESOURCE
from ..forms import resource as resource_forms
from ..models import Resource


# NB: Resource not registered as CremeEntity
class ResourceCreation(generic.AddingInstanceToEntityPopup):
    model = Resource
    form_class = resource_forms.ResourceCreateForm
    title = _('Allocation of a new resource')
    entity_classes = get_task_model()
    entity_id_url_kwarg = 'task_id'
    entity_form_kwarg = 'task'

    def check_related_entity_permissions(self, entity, user):
        super().check_related_entity_permissions(entity=entity, user=user)

        if not entity.is_alive():
            raise ConflictError(
                gettext(
                    "You can't add a resource or a working "
                    "period to a task which has status «{}»"
                ).format(entity.tstatus.name)
            )


class ResourceEdition(generic.RelatedToEntityEditionPopup):
    model = Resource
    form_class = resource_forms.ResourceEditForm
    permissions = 'projects'
    pk_url_kwarg = 'resource_id'
    title = _('Resource for «{entity}»')


class ResourceDeletion(generic.CremeModelDeletion):
    model = Resource
    permissions = 'projects'

    def check_instance_permissions(self, instance, user):
        user.has_perm_to_change_or_die(instance.task)
        # NB: beware to change template if uncommented
        # request.user.has_perm_to_delete_or_die(resource)

        if Relation.objects.filter(
            subject_entity=instance.linked_contact_id,
            type=REL_SUB_PART_AS_RESOURCE,
            object_entity__in=[a.id for a in instance.task.related_activities],
        ).exists():
            raise ConflictError(
                gettext('This resource cannot be deleted, because it is linked to activities.')
            )
