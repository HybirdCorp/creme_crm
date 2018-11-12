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


# @login_required
# @permission_required('projects')
# # @permission_required('projects.add_resource') #resource not registered as CremeEntity
# def add(request, task_id):
#     # return utils._add_generic(request, resource_forms.ResourceCreateForm, task_id, _(u'Allocation of a new resource'))
#     task = get_object_or_404(get_task_model(), pk=task_id)
#     user = request.user
#
#     user.has_perm_to_change_or_die(task)
#
#     if not task.is_alive():
#         raise ConflictError(ugettext(u"You can't add a resources or a working "
#                                      u"period to a task which has status «{}»"
#                                     ).format(task.tstatus.name)
#                            )
#
#     if request.method == 'POST':
#         form = resource_forms.ResourceCreateForm(task, user=user, data=request.POST)
#
#         if form.is_valid():
#             form.save()
#     else:
#         form = resource_forms.ResourceCreateForm(task, user=user)
#
#     return generic.inner_popup(request, 'creme_core/generics/blockform/add_popup.html',
#                                {'form':         form,
#                                 'title':        _('Allocation of a new resource'),
#                                 'submit_label': Resource.save_label,
#                                },
#                                is_valid=form.is_valid(),
#                                reload=False,
#                                delegate_reload=True,
#                               )
class ResourceCreation(generic.AddingToEntityPopup):  # NB: Resource not registered as CremeEntity
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

# @login_required
# @permission_required('projects')
# def edit(request, resource_id):
#     return generic.edit_related_to_entity(request, pk=resource_id, model=Resource,
#                                           form_class=resource_forms.ResourceEditForm,
#                                           title_format=_('Resource for «%s»'),
#                                          )
class ResourceEdition(generic.RelatedToEntityEditionPopup):
    model = Resource
    form_class = resource_forms.ResourceEditForm
    permissions = 'projects'
    pk_url_kwarg = 'resource_id'
    title_format = _('Resource for «{}»')


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
