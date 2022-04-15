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

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.workflow import (
    WorkflowConditions,
    wf_efilter_registry,
    workflow_registry,
)
from creme.creme_core.forms import CremeModelForm, FieldBlockManager
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms.widgets import CremeRadioSelect
from creme.creme_core.models import CremeEntity, Workflow


class _WorkflowWizardFormStep(CremeModelForm):
    class Meta:
        model = Workflow
        fields: tuple[str, ...] = ()


# Fields ------------------------------------------------------------------------
class TriggerField(core_fields.UnionField):
    # TODO: argument to pass workflow_registry
    def __init__(self, model=CremeEntity, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model
        self.fields_choices = [
            (
                trigger_cls.type_id,
                trigger_cls.config_formfield(model=model)
            ) for trigger_cls in workflow_registry.trigger_classes
        ]


# Forms ------------------------------------------------------------------------
class TriggerStep(_WorkflowWizardFormStep):
    trigger = TriggerField(
        label=_('Trigger'),
        help_text=_('Which kind of event will trigger the Workflow?'),
    )

    class Meta(_WorkflowWizardFormStep.Meta):
        fields = ('title',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trigger'].model = self.instance.content_type.model_class()

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            # [0] == trigger class ID
            self.instance.trigger = cdata['trigger'][1]

        return cdata


class ConditionsStep(_WorkflowWizardFormStep):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields

        self.conditions_field_names = fnames = []
        f_kwargs = {
            'user': self.user,
            'required': False,
            'efilter_type': wf_efilter_registry.id,
        }
        for source in self.instance.trigger.root_sources():
            source_fnames = []

            for handler_cls in wf_efilter_registry.handler_classes:
                fname = f"{source.type_id}-{handler_cls.__name__.lower().replace('handler', '')}"
                fields[fname] = field = handler_cls.formfield(**f_kwargs)

                field.initialize(ContentType.objects.get_for_model(source.model))
                source_fnames.append(fname)

            fnames.append((source, source_fnames))

    # TODO: unit test
    def get_blocks(self):
        user = self.user

        return FieldBlockManager(*[
            {
                'id': f'conditions_{source.type_id}',
                'label': gettext('Conditions on «{source}»').format(
                    source=source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
                ),
                'fields': field_names,
            } for source, field_names in self.conditions_field_names
        ]).build(self)

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            conditions = WorkflowConditions()
            for source, field_names in self.conditions_field_names:
                conditions.add(
                    source=source,
                    conditions=[cond for fname in field_names for cond in cdata[fname]],
                )

            self.instance.conditions = conditions

        return cdata


class ActionTypeStep(_WorkflowWizardFormStep):
    action_type = forms.ChoiceField(
        label=_('Type of action'), widget=CremeRadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action_type'].choices = [
            (action_cls.type_id, action_cls.verbose_name)
            for action_cls in workflow_registry.action_classes
        ]


class WorkflowRenamingForm(CremeModelForm):
    class Meta:
        model = Workflow
        fields = ('title',)


# TODO: factorise with ConditionsStep
class WorkflowConditionsEditionForm(CremeModelForm):
    class Meta:
        model = Workflow
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields

        self.conditions_field_names = fnames = []
        f_kwargs = {
            'user': self.user,
            'required': False,
            'efilter_type': wf_efilter_registry.id,
        }
        workflow  = self.instance
        conditions = workflow.conditions

        for source in workflow.trigger.root_sources():
            source_fnames = []

            for handler_cls in wf_efilter_registry.handler_classes:
                fname = f"{source.type_id}-{handler_cls.__name__.lower().replace('handler', '')}"
                fields[fname] = field = handler_cls.formfield(**f_kwargs)

                field.initialize(
                    ctype=ContentType.objects.get_for_model(source.model),
                    conditions=conditions.conditions_for_source(source),
                )
                source_fnames.append(fname)

            fnames.append((source, source_fnames))

    # TODO: unit test
    def get_blocks(self):
        user = self.user

        return FieldBlockManager(*[
            {
                'id': f'conditions_{source.type_id}',
                'label': gettext('Conditions on «{source}»').format(
                    source=source.render(user=user, mode=source.RenderMode.TEXT_PLAIN),
                ),
                'fields': field_names,
            } for source, field_names in self.conditions_field_names
        ]).build(self)

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        conditions = WorkflowConditions()
        for source, field_names in self.conditions_field_names:
            conditions.add(
                source=source,
                conditions=[cond for fname in field_names for cond in cdata[fname]],
            )

        self.instance.conditions = conditions

        return super().save(*args, **kwargs)
