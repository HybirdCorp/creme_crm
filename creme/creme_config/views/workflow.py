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

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import Workflow
from creme.creme_core.utils import get_from_POST_or_404
# from creme.creme_core.views.generic.base import EntityCTypeRelatedMixin
from creme.creme_core.views import generic

from ..forms import workflow as workflow_forms
from . import base


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/workflow.html'


# TODO: generic config view for that (see user_role)?
class WorkflowCreationWizard(generic.base.EntityCTypeRelatedMixin,
                             base.ConfigModelCreationWizard):
    form_list = [
        workflow_forms.TriggerStep,
        workflow_forms.ConditionsStep,
        workflow_forms.FirstActionSelectionStep,
        workflow_forms.FirstActionCreationStep,
    ]
    model = Workflow

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow = Workflow(enabled=False)

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


class WorkflowEnabling(generic.CheckedView):
    permissions = base._PERM
    pk_url_kwarg = 'workflow_id'
    enabled_arg = 'enabled'
    enabled_default = True

    def post(self, *args, **kwargs):
        Workflow.objects.filter(id=kwargs[self.pk_url_kwarg]).update(
            enabled=kwargs.get(self.enabled_arg, self.enabled_default),
        )

        return HttpResponse()


class WorkflowDeletion(base.ConfigDeletion):
    id_arg = 'id'

    def perform_deletion(self, request):
        wf = get_object_or_404(
            Workflow, id=get_from_POST_or_404(request.POST, self.id_arg),
        )

        if not wf.is_custom:
            raise ConflictError(_('This Workflow cannot be deleted'))

        wf.delete()
