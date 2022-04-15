################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

# from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

# from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Workflow
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views.generic import BricksView
from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin

from ..forms import workflow as workflow_forms
from . import base


class Portal(BricksView):
    template_name = 'creme_config/portals/workflow.html'


# TODO: generic config view for that (see user_role)?
class WorkflowCreationWizard(EntityCTypeRelatedMixin,
                             base.ConfigModelCreationWizard):
    form_list = [
        workflow_forms.TriggerStep,
        workflow_forms.ConditionsStep,
        workflow_forms.FirstActionSelectionStep,
    ]
    model = Workflow

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow = Workflow()

    # TODO?
    # def done_save(self, form_list):
    #     for form in form_list:
    #         form.save()

    def get_form_instance(self, step):
        wf = self.workflow
        wf.content_type = self.get_ctype()

        # We fill the instance with the previous step
        # (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return wf

    def get_title(self):
        return _('Create a workflow for «{model}»').format(model=self.get_ctype())


class WorkflowDeletion(base.ConfigDeletion):
    id_arg = 'id'

    # TODO: is_custom??
    def perform_deletion(self, request):
        Workflow.objects.filter(id=get_from_POST_or_404(request.POST, self.id_arg),).delete()
