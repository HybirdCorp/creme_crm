# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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
import warnings

from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from creme.activities import get_activity_model

from creme import projects
from .. import constants
from ..forms import task as task_forms


logger = logging.getLogger(__name__)
Activity = get_activity_model()
ProjectTask = projects.get_task_model()


def abstract_add_ptask(request, project_id, form=task_forms.TaskCreateForm,
                       title=_('Create a task for «%s»'),
                       submit_label=ProjectTask.save_label,
                      ):
    warnings.warn('projects.views.task.abstract_add_ptask() is deprecated ; '
                  'use the class-based view TaskCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_to_entity(request, project_id, form, title,
                                 entity_class=projects.get_project_model(),
                                 submit_label=submit_label,
                                )


def abstract_edit_ptask(request, task_id, form=task_forms.TaskEditForm):
    warnings.warn('projects.views.task.abstract_edit_ptask() is deprecated ; '
                  'use the class-based view TaskEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, task_id, ProjectTask, form)


def abstract_edit_ptask_popup(request, task_id, form=task_forms.TaskEditForm):
    warnings.warn('projects.views.task.abstract_edit_ptask_popup() is deprecated ; '
                  'use the class-based view TaskEditionPopup instead.',
                  DeprecationWarning
                 )
    return generic.edit_model_with_popup(request, {'pk': task_id}, ProjectTask, form)
# todo: ?
#    return edit_related_to_entity(request, task_id, ProjectTask,
#                                  TaskEditForm, _(u'Edit a task for «%s»'),
#                                 )


def abstract_view_ptask(request, task_id,
                        template='projects/view_task.html',
                       ):
    warnings.warn('projects.views.task.abstract_view_ptask() is deprecated ; '
                  'use the class-based view TaskDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, task_id, ProjectTask, template=template)


@login_required
@permission_required(('projects', cperm(ProjectTask)))
def add(request, project_id):
    warnings.warn('projects.views.task.add() is deprecated.', DeprecationWarning)
    return abstract_add_ptask(request, project_id)


@login_required
@permission_required('projects')
def detailview(request, task_id):
    warnings.warn('projects.views.task.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_ptask(request, task_id)


@login_required
@permission_required('projects')
def edit(request, task_id):
    warnings.warn('projects.views.task.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_ptask(request, task_id)


@login_required
@permission_required('projects')
def edit_popup(request, task_id):
    warnings.warn('projects.views.task.edit_popup() is deprecated.', DeprecationWarning)
    return abstract_edit_ptask_popup(request, task_id)


# @login_required
# @permission_required('projects')
# def add_parent(request, task_id):
#     return generic.edit_model_with_popup(request, {'pk': task_id}, ProjectTask, task_forms.TaskAddParentForm)


@login_required
@permission_required('projects')
def delete_parent(request):
    POST = request.POST
    parent_id = get_from_POST_or_404(POST, 'parent_id')
    task = get_object_or_404(ProjectTask, pk=get_from_POST_or_404(POST, 'id'))
    user = request.user

    # user.has_perm_to_change_or_die(task.project) #beware: modify block_tasks.html template if uncommented....
    user.has_perm_to_change_or_die(task)

    task.parent_tasks.remove(parent_id)

    return HttpResponse()


# Class-based views  ----------------------------------------------------------

class TaskCreation(generic.AddingToEntityPopup):
    model = ProjectTask
    form_class = task_forms.TaskCreateForm
    title_format = _('Create a task for «{}»')
    entity_id_url_kwarg = 'project_id'
    entity_classes = projects.get_project_model()

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        self.request.user.has_perm_to_create_or_die(ProjectTask)


class TaskDetail(generic.EntityDetail):
    model = ProjectTask
    template_name = 'projects/view_task.html'
    pk_url_kwarg = 'task_id'


class TaskEdition(generic.EntityEdition):
    model = ProjectTask
    form_class = task_forms.TaskEditForm
    pk_url_kwarg = 'task_id'


class TaskEditionPopup(generic.EntityEditionPopup):
    model = ProjectTask
    form_class = task_forms.TaskEditForm
    pk_url_kwarg = 'task_id'


class ParentsAdding(generic.EntityEditionPopup):
    model = ProjectTask
    form_class = task_forms.TaskAddParentForm
    pk_url_kwarg = 'task_id'
    title_format = _('Adding parents to «{}»')


class ActivityEditionPopup(generic.EntityEditionPopup):
    model = Activity
    # NB: the form checks that the Activity is related to a task
    form_class = task_forms.RelatedActivityEditForm
    pk_url_kwarg = 'activity_id'


# Activities -------------------------------------------------------------------

# def abstract_add_activity(request, task_id, form=task_forms.RelatedActivityCreateForm,
#                           title=_('New activity related to «%s»'),
#                           submit_label=Activity.save_label,
#                          ):
#     task = get_object_or_404(ProjectTask, pk=task_id)
#     user = request.user
#
#     user.has_perm_to_change_or_die(task)  # todo: has_perm_to_link_or_die ??
#
#     return generic.add_model_with_popup(request, form,
#                                         title=title % task.allowed_str(user),
#                                         initial={'task': task},
#                                         submit_label=submit_label,
#                                        )


def abstract_edit_activity(request, activity_id, form=task_forms.RelatedActivityEditForm):
    warnings.warn('projects.views.task.abstract_edit_activity() is deprecated ; '
                  'use the class-based view ActivityEditionPopup instead.',
                  DeprecationWarning
                 )
    return generic.edit_model_with_popup(request, {'pk': activity_id}, Activity, form)


# @login_required
# @permission_required(('projects', cperm(Activity)))
# def add_activity(request, task_id):
#     return abstract_add_activity(request, task_id)


# TODO: LINK perm instead of CHANGE ?
class RelatedActivityCreation(generic.AddingToEntityPopup):
    model = Activity
    form_class = task_forms.RelatedActivityCreateForm
    permissions = cperm(Activity)
    title_format = _('New activity related to «{}»')
    entity_id_url_kwarg = 'task_id'
    entity_classes = ProjectTask


@login_required
@permission_required('projects')
def edit_activity(request, activity_id):
    warnings.warn('projects.views.task.edit_activity() is deprecated.', DeprecationWarning)
    return abstract_edit_activity(request, activity_id)


@login_required
@permission_required('projects')
def delete_activity(request):
    activity = get_object_or_404(Activity, pk=request.POST.get('id'))
    get_rel = Relation.objects.get

    try:
        rel1 = get_rel(type=constants.REL_SUB_PART_AS_RESOURCE, object_entity=activity)
        rel2 = get_rel(subject_entity=activity, type=constants.REL_SUB_LINKED_2_PTASK)
    except Relation.DoesNotExist as e:
        raise ConflictError('This activity is not related to a project task.') from e

    request.user.has_perm_to_change_or_die(rel2.object_entity.get_real_entity())  # Project task

    try:
        rel1.delete()
        rel2.delete()
        activity.delete()
    except ProtectedError:
        logger.exception('Error when deleting an activity of project')
        status = 409
        msg = ugettext('Can not be deleted because of its dependencies.')
    except Exception as e:
        status = 400
        msg = ugettext('The deletion caused an unexpected error [{}].').format(e)
    else:
        msg = ugettext('Operation successfully completed')
        status = 200

    return HttpResponse(msg, status=status)
