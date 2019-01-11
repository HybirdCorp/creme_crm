# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import get_task_model
from ..constants import REL_SUB_PART_AS_RESOURCE
from ..forms import resource as resource_forms
from ..models import Resource


class ResourceCreation(generic.AddingInstanceToEntityPopup):  # NB: Resource not registered as CremeEntity
    model = Resource
    form_class = resource_forms.ResourceCreateForm
    title = _('Allocation of a new resource')
    entity_classes = get_task_model()
    entity_id_url_kwarg = 'task_id'
    entity_form_kwarg = 'task'

    def check_related_entity_permissions(self, entity, user):
        super().check_related_entity_permissions(entity=entity, user=user)

        if not entity.is_alive():
            raise ConflictError(ugettext("You can't add a resource or a working "
                                         "period to a task which has status «{}»"
                                        ).format(entity.tstatus.name)
                               )


class ResourceEdition(generic.RelatedToEntityEditionPopup):
    model = Resource
    form_class = resource_forms.ResourceEditForm
    permissions = 'projects'
    pk_url_kwarg = 'resource_id'
    title = _('Resource for «{entity}»')


@login_required
@permission_required('projects')
def delete(request):  # TODO: generic delete ??
    resource = get_object_or_404(Resource, pk=get_from_POST_or_404(request.POST, 'id'))

    request.user.has_perm_to_change_or_die(resource.task)
    # request.user.has_perm_to_delete_or_die(resource) #beware to change template if uncommented

    if Relation.objects.filter(subject_entity=resource.linked_contact_id,
                               type=REL_SUB_PART_AS_RESOURCE,
                               object_entity__in=[a.id for a in resource.task.related_activities],
                              ) \
                       .exists():
        raise ConflictError(ugettext('This resource cannot be deleted, because it is linked to activities.'))

    resource.delete()

    return HttpResponse()
