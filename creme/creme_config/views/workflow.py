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

from django.forms import Form
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import workflow_registry
from creme.creme_core.models import Workflow
from creme.creme_core.utils import get_from_POST_or_404
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
        # NB: this last form is just a placeholder;
        #     it will be dynamically replaced by an Action (see get_form()).
        Form,
    ]
    model = Workflow

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow = Workflow(enabled=False)

    # TODO? (<Workflow.save()> called several times?)
    # def done_save(self, form_list):
    #     for form in form_list:
    #         form.save()

    def get_form(self, step=None, data=None, files=None):
        form = None

        # Step can be None (see WizardView doc)
        if step is None:
            step = self.steps.current

        if step == '3':
            # TODO: registry in attr
            prev_data = self.get_cleaned_data_for_step('2')
            # TODO: get_action_class()
            action_cls = {
                cls.type_id: cls
                for cls in workflow_registry.action_classes
            }[prev_data['action_type']]

            form_cls = action_cls.config_form_class()

            kwargs = self.get_form_kwargs(step)
            kwargs.update(
                data=data,
                files=files,
                prefix=self.get_form_prefix(step, None),
                initial=self.get_form_initial(step),  # Not really useful here...
                instance=self.get_form_instance(step),
            )

            form = form_cls(**kwargs)
        else:
            form = super().get_form(step, data, files)

        return form

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
