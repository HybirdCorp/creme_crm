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
from django.db.models import ProtectedError, Q
from django.db.transaction import atomic
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme import projects
from creme.activities import get_activity_model
from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import run_workflow_engine
from creme.creme_core.models import Relation
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from .. import custom_forms
from ..constants import REL_SUB_LINKED_2_PTASK, REL_SUB_PART_AS_RESOURCE
from ..forms import task as task_forms

logger = logging.getLogger(__name__)
Activity = get_activity_model()
ProjectTask = projects.get_task_model()


class TaskCreation(generic.AddingInstanceToEntityPopup):
    model = ProjectTask
    form_class = custom_forms.TASK_CREATION_CFORM
    title = _('Create a task for «{entity}»')
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
    form_class = custom_forms.TASK_EDITION_CFORM
    pk_url_kwarg = 'task_id'


class TaskEditionPopup(generic.EntityEditionPopup):
    model = ProjectTask
    form_class = custom_forms.TASK_EDITION_CFORM
    pk_url_kwarg = 'task_id'


class ParentsAdding(generic.EntityEditionPopup):
    model = ProjectTask
    form_class = task_forms.TaskParentsAddingForm
    pk_url_kwarg = 'task_id'
    title = _('Adding parents to «{object}»')


class ParentRemoving(generic.base.EntityRelatedMixin, generic.CremeDeletion):
    permissions = 'projects'
    entity_classes = ProjectTask

    task_id_arg = 'id'
    parent_id_arg = 'parent_id'

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, self.task_id_arg, cast=int)

    def perform_deletion(self, request):
        parent_id = get_from_POST_or_404(request.POST, self.parent_id_arg)

        with atomic(), run_workflow_engine(user=request.user):
            self.get_related_entity().parent_tasks.remove(parent_id)


class ActivityEditionPopup(generic.EntityEditionPopup):
    model = Activity
    # NB: the form checks that the Activity is related to a task
    form_class = task_forms.RelatedActivityEditionForm
    pk_url_kwarg = 'activity_id'


# Activities -------------------------------------------------------------------


# TODO: LINK perm instead of CHANGE ?
class RelatedActivityCreation(generic.AddingInstanceToEntityPopup):
    model = Activity
    form_class = task_forms.RelatedActivityCreationForm
    permissions = cperm(Activity)
    title = _('New activity related to «{entity}»')
    entity_id_url_kwarg = 'task_id'
    entity_classes = ProjectTask


class ActivityDeletion(generic.CremeModelDeletion):
    model = Activity
    permissions = 'projects'

    def get_relations(self, activity):
        relations = {
            r.type_id: r
            for r in Relation.objects.filter(
                Q(type=REL_SUB_PART_AS_RESOURCE, object_entity=activity)
                | Q(subject_entity=activity, type=REL_SUB_LINKED_2_PTASK)
            )[:2]
        }

        ptask_rel = relations.get(REL_SUB_LINKED_2_PTASK)

        if ptask_rel is None or REL_SUB_PART_AS_RESOURCE not in relations:
            raise ConflictError('This activity is not related to a project task.')

        # TODO: unit test
        self.request.user.has_perm_to_change_or_die(
            ptask_rel.real_object  # Project task
        )

        return relations

    def perform_deletion(self, request):
        # TODO: factorise
        if not settings.ENTITIES_DELETION_ALLOWED:
            raise ConflictError(
                gettext('The definitive deletion has been disabled by the administrator.')
            )

        activity = self.object = self.get_object()
        relations = self.get_relations(activity)

        try:
            with atomic(), run_workflow_engine(user=request.user):
                for rel in relations.values():
                    rel.delete()

                activity.delete()
        except ProtectedError as e:
            logger.exception('Error when deleting an activity of project')

            raise ConflictError(
                'Can not be deleted because of its dependencies.'
            ) from e
