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
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.core.workflow import workflow_registry
from creme.creme_core.models import CustomEntityType, Workflow
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..bricks import WorkflowsBrick
from ..forms import workflow as workflow_forms
from . import base


class Portal(base.ConfigPortal):
    template_name = 'creme_config/portals/workflow.html'
    brick_classes = [WorkflowsBrick]


# Workflow ---------------------------------------------------------------------
# TODO: generic config view for that (see user_role)?
class WorkflowCreationWizard(generic.base.EntityCTypeRelatedMixin,
                             base.ConfigModelCreationWizard):
    form_list = [
        workflow_forms.TriggerStep,
        workflow_forms.ConditionsStep,
        workflow_forms.ActionTypeStep,
        # NB: this last form is just a placeholder;
        #     it will be dynamically replaced by an Action (see get_form()).
        Form,
    ]
    model = Workflow

    def __init__(self, *args, registry=workflow_registry, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = registry
        self.workflow = Workflow(enabled=False)

    def get_ctype(self):
        ctype = super().get_ctype()

        ce_type = CustomEntityType.objects.get_for_model(ctype.model_class())
        if ce_type and not ce_type.enabled:
            raise ConflictError(gettext('This custom type does not exist anymore.'))

        return ctype

    def get_form(self, step=None, data=None, files=None):
        form = None

        # Step can be None (see WizardView doc)
        if step is None:
            step = self.steps.current

        if step == '3':
            prev_data = self.get_cleaned_data_for_step('2')
            action_cls = self.registry.get_action_class(prev_data['action_type'])
            if action_cls is None:
                raise Http404('Invalid action type')

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
        return gettext('Create a Workflow for «{model}»').format(model=self.get_ctype())


class WorkflowRenaming(base.ConfigModelEdition):
    model = Workflow
    form_class = workflow_forms.WorkflowRenamingForm
    pk_url_kwarg = 'workflow_id'
    title = _('Rename «{object}»')


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
            raise ConflictError(gettext('This Workflow cannot be deleted'))

        wf.delete()


# Actions ----------------------------------------------------------------------

# TODO: factorise with 'WorkflowCreationWizard'
class WorkflowActionAddingWizard(base.ConfigModelEditionWizard):
    model = Workflow
    pk_url_kwarg = 'workflow_id'

    form_list = [
        workflow_forms.ActionTypeStep,
        # NB: this last form is just a placeholder;
        #     it will be dynamically replaced by an Action (see get_form()).
        Form,
    ]
    # Translators: 'object' is a Workflow
    title = _('Add an action to «{object}»')

    def __init__(self, registry=workflow_registry, **kwargs):
        super().__init__(**kwargs)
        self.registry = registry

    def check_instance_permissions(self, instance, user):
        if not instance.is_custom:
            raise ConflictError(gettext('This Workflow cannot be edited'))

    def get_form(self, step=None, data=None, files=None):
        form = None

        # Step can be None (see WizardView doc)
        if step is None:
            step = self.steps.current

        if step == '1':
            prev_data = self.get_cleaned_data_for_step('0')

            action_cls = self.registry.get_action_class(prev_data['action_type'])
            if action_cls is None:
                raise Http404('Invalid action type')

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


class WorkflowConditionsEdition(base.ConfigModelEdition):
    model = Workflow
    form_class = workflow_forms.WorkflowConditionsEditionForm
    pk_url_kwarg = 'workflow_id'
    # Translators: 'object' is a Workflow
    title = _('Edit the conditions of «{object}»')

    def check_instance_permissions(self, instance, user):
        if not instance.is_custom:
            raise ConflictError(gettext('This Workflow cannot be edited'))


class WorkflowActionEdition(base.ConfigModelEdition):
    model = Workflow
    pk_url_kwarg = 'workflow_id'
    title = _('Edit the action «{action}»')

    def get_action_index(self):
        return int(self.kwargs['action_index'])

    def get_action(self):
        try:
            return self.object.actions[self.get_action_index()]
        except IndexError as e:
            raise Http404(gettext('This action does not exist anymore')) from e

    def get_form_class(self):
        return self.get_action().config_form_class()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['action_index'] = self.get_action_index()

        return kwargs

    def get_title_format_data(self):
        data = super().get_title_format_data()
        data['action'] = self.get_action()

        return data


class WorkflowActionDeletion(base.ConfigDeletion):
    index_arg = 'index'

    def perform_deletion(self, request) -> None:
        wf: Workflow = get_object_or_404(Workflow, id=self.kwargs['workflow_id'])

        # TODO: factorise
        if not wf.is_custom:
            raise ConflictError(gettext('This Workflow cannot be edited'))

        actions = [*wf.actions]
        try:
            actions.pop(get_from_POST_or_404(request.POST, self.index_arg, cast=int))
        except IndexError as e:
            raise ConflictError(
                gettext('This action is invalid (refresh your page)')
            ) from e

        wf.actions = actions
        wf.save()
