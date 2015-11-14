# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404 # redirect
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import (add_to_entity,add_model_with_popup,
        view_entity, edit_entity, edit_model_with_popup) #edit_related_to_entity

from creme.activities import get_activity_model
# from creme.activities.models import Activity

from .. import get_project_model, get_task_model
from ..constants import REL_SUB_PART_AS_RESOURCE, REL_SUB_LINKED_2_PTASK
from ..forms.task import (TaskCreateForm, TaskEditForm, TaskAddParentForm,
        RelatedActivityCreateForm, RelatedActivityEditForm)
#from ..models import ProjectTask #Project


logger = logging.getLogger(__name__)
Activity = get_activity_model()
ProjectTask = get_task_model()


def abstract_add_ptask(request, project_id, form=TaskCreateForm,
                       title=_(u'Add a task to «%s»'),
                       submit_label=_('Save the task'),
                       ):
    return add_to_entity(request, project_id, form, title,
#                         entity_class=Project,
                         entity_class=get_project_model(),
                         submit_label=submit_label,
                        )


def abstract_edit_ptask(request, task_id, form=TaskEditForm):
    return edit_entity(request, task_id, ProjectTask, form)


def abstract_edit_ptask_popup(request, task_id, form=TaskEditForm):
    return edit_model_with_popup(request, {'pk': task_id}, ProjectTask, form)
# TODO: ?
#    return edit_related_to_entity(request, task_id, ProjectTask,
#                                  TaskEditForm, _(u'Edit a task for «%s»'),
#                                 )

def abstract_view_ptask(request, task_id,
                        template='projects/view_task.html',
                       ):
    return view_entity(request, task_id, ProjectTask, path='/projects/task',
                       template=template,
                      )


@login_required
# @permission_required(('projects', 'projects.add_projecttask'))
@permission_required(('projects', cperm(ProjectTask)))
def add(request, project_id):
    return abstract_add_ptask(request, project_id)


@login_required
@permission_required('projects')
#def detailview(request, object_id):
def detailview(request, task_id):
    return abstract_view_ptask(request, task_id)


@login_required
@permission_required('projects')
def edit(request, task_id):
    return abstract_edit_ptask(request, task_id)


@login_required
@permission_required('projects')
def edit_popup(request, task_id):
    return abstract_edit_ptask_popup(request, task_id)


@login_required
@permission_required('projects')
def add_parent(request, task_id):
    return edit_model_with_popup(request, {'pk': task_id}, ProjectTask, TaskAddParentForm)

#@login_required
#@permission_required('projects')
#def delete(request):
#    task = get_object_or_404(ProjectTask, pk=request.POST.get('id'))
#    project = task.project
#    user = request.user
#
#    user.has_perm_to_change_or_die(project)
#    user.has_perm_to_delete_or_die(task)
#
#    task.delete()
#
#    if request.is_ajax():
#        return HttpResponse()
#
#    return redirect(project)

@login_required
@permission_required('projects')
def delete_parent(request):
    POST = request.POST
    parent_id = get_from_POST_or_404(POST, 'parent_id')
    task = get_object_or_404(ProjectTask, pk=get_from_POST_or_404(POST, 'id'))
    user = request.user

    #user.has_perm_to_change_or_die(task.project) #beware: modify block_tasks.html template if uncommented....
    user.has_perm_to_change_or_die(task)

    task.parent_tasks.remove(parent_id)

    return HttpResponse("")


# Activities -------------------------------------------------------------------

def abstract_add_activity(request, task_id, form=RelatedActivityCreateForm,
                          title=_(u'New activity related to «%s»'),
                          submit_label=_('Save the activity'),
                         ):
    task = get_object_or_404(ProjectTask, pk=task_id)
    user = request.user

    user.has_perm_to_change_or_die(task)  # TODO: has_perm_to_link_or_die ??

    return add_model_with_popup(request, form,
                                title=title % task.allowed_unicode(user),
                                initial={'task': task},
                                submit_label=submit_label,
                               )


def abstract_edit_activity(request, activity_id, form=RelatedActivityEditForm):
    # TODO: check that its related to a task
    return edit_model_with_popup(request, {'pk': activity_id}, Activity, form)


@login_required
# @permission_required(('projects', 'activities.add_activity'))
@permission_required(('projects', cperm(Activity)))
def add_activity(request, task_id):
    return abstract_add_activity(request, task_id)


@login_required
@permission_required('projects')
def edit_activity(request, activity_id):
    return abstract_edit_activity(request, activity_id)


@login_required
@permission_required('projects')
def delete_activity(request):
#    activity = get_object_or_404(Activity, pk=request.POST.get('id'))
    activity = get_object_or_404(get_activity_model(), pk=request.POST.get('id'))
    get_rel = Relation.objects.get

    try:
        rel1 = get_rel(type=REL_SUB_PART_AS_RESOURCE, object_entity=activity)
        rel2 = get_rel(subject_entity=activity, type=REL_SUB_LINKED_2_PTASK)
    except Relation.DoesNotExist:
        raise ConflictError('This activity is not related to a project task.')

    request.user.has_perm_to_change_or_die(rel2.object_entity.get_real_entity()) #project task

    try:
        rel1.delete()
        rel2.delete()
        activity.delete()
    except ProtectedError:
        logger.exception('Error when deleting an activity of project')
        status = 409
        msg = ugettext(u'Can not be deleted because of its dependencies.')
    except Exception as e:
        status = 400
        msg = ugettext(u'The deletion caused an unexpected error [%s].') % e
    else:
        msg = ugettext('Operation successfully completed')
        status = 200

    return HttpResponse(msg, status=status)
