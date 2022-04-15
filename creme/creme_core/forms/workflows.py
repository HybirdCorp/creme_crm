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
from django.core.exceptions import ValidationError
from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy as _

from creme.creme_core import forms as core_forms
from creme.creme_core import workflows as core_workflows
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.core.workflow import (
    WorkflowAction,
    WorkflowSource,
    workflow_registry,
)
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms import widgets as core_widgets
from creme.creme_core.models import (
    CremeEntity,
    CremePropertyType,
    RelationType,
    Workflow,
)
from creme.creme_core.utils.url import TemplateURLBuilder


# Widgets ----------------------------------------------------------------------
# TODO: move to core fields?
class RelationToCTypeSelector(core_widgets.ChainedInput):
    def __init__(self, relation_types=(), attrs=None):
        super().__init__(attrs)
        self.relation_types = relation_types

    def get_context(self, name, value, attrs):
        dselect_attrs = {'auto': False, 'autocomplete': True}

        self.add_dselect(
            'rtype', options=self.relation_types, attrs=dselect_attrs,
            avoid_empty=True,
        )
        self.add_dselect(
            'ctype',
            options=TemplateURLBuilder(
                rtype_id=(TemplateURLBuilder.Word, '${rtype}'),
            ).resolve('creme_core__ctypes_compatible_with_rtype'),  # TODO: self.ctypes_url?
            attrs=dselect_attrs,
            avoid_empty=True,
        )

        return super().get_context(name=name, value=value, attrs=attrs)


# Fields -----------------------------------------------------------------------
# Triggers ---
class _EntityTriggerField(forms.Field):
    widget = forms.HiddenInput
    # NB: override in child classes
    trigger_class = core_workflows.WorkflowTrigger

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        return self.trigger_class(model=self.model)


class EntityCreationTriggerField(_EntityTriggerField):
    trigger_class = core_workflows.EntityCreationTrigger


class EntityEditionTriggerField(_EntityTriggerField):
    trigger_class = core_workflows.EntityEditionTrigger


class PropertyAddingTriggerField(forms.ModelChoiceField):
    def __init__(self, model, **kwargs):
        super().__init__(**{
            **kwargs,
            'queryset': CremePropertyType.objects.none(),
        })
        self.model = model

    def clean(self, value):
        ptype = super().clean(value)

        return core_workflows.PropertyAddingTrigger(
            entity_model=self.model, ptype=ptype,
        )  if ptype else None

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model
        self.queryset = CremePropertyType.objects.compatible(model)


class RelationAddingTriggerField(core_fields.JSONField):
    widget = RelationToCTypeSelector
    default_error_messages = {
        'rtypenotallowed': _(
            'This type of relationship does not exist or causes a constraint error'
        ),
        'forbiddenctype': _('This type of entity causes a constraint error'),
    }
    value_type = dict  # See JSONField

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model
        # TODO: do not exclude a disabled rtype which is used (edition context)
        self._rtypes = RelationType.objects.compatible(
            model, include_internals=True,
        ).exclude(enabled=False)
        self.widget.relation_types = core_fields.ChoiceModelIterator(
            queryset=self._rtypes,
        )

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        ctype = self._clean_ctype(ctype_id=clean_value(data, 'ctype',  int, required=False))
        rtype = self._clean_rtype(rtype_pk=clean_value(data, 'rtype',  str))

        if not rtype.symmetric_type.is_compatible(ctype):
            raise ValidationError(
                self.error_messages['forbiddenctype'],
                code='forbiddenctype',
            )

        return core_workflows.RelationAddingTrigger(
            subject_model=self._model,
            rtype=rtype,
            object_model=ctype.model_class(),
        )

    def _clean_rtype(self, rtype_pk):
        rtypes = self._rtypes

        try:
            rtype = rtypes.get(pk=rtype_pk)
        except rtypes.model.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['rtypenotallowed'],
                code='rtypenotallowed',
            ) from e

        return rtype

    def _value_to_jsonifiable(self, value):
        return {
            'rtype': value.relation_type.id,
            'ctype': ContentType.objects.get_for_model(value.object_model).id,
        }


# Sources ---
class _FromContextSourceField(forms.Field):
    widget = forms.HiddenInput
    # NB: override in child classes
    source_class = core_workflows.FromContextSource

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        return self.source_class(model=self.model)

    def prepare_value(self, value):
        return ''


class CreatedEntitySourceField(_FromContextSourceField):
    source_class = core_workflows.CreatedEntitySource


class EditedEntitySourceField(_FromContextSourceField):
    source_class = core_workflows.EditedEntitySource


class TaggedEntitySourceField(_FromContextSourceField):
    source_class = core_workflows.TaggedEntitySource


class SubjectEntitySourceField(_FromContextSourceField):
    source_class = core_workflows.SubjectEntitySource


class ObjectEntitySourceField(_FromContextSourceField):
    source_class = core_workflows.ObjectEntitySource


class FixedEntitySourceField(core_fields.GenericEntityField):
    def __init__(self, **kwargs):
        super().__init__(**{
            **kwargs,
            'required': False,
            'credentials': EntityCredentials.VIEW,  # TODO: unit test
        })

    def clean(self, value):
        entity = super().clean(value)

        return core_workflows.FixedEntitySource(entity=entity) if entity else None

    def _value_to_jsonifiable(self, value):
        return super()._value_to_jsonifiable(value=value.entity)


# TODO: manage hidden fields?
class EntityFKSourceField(forms.ChoiceField):
    def __init__(self, entity_source, **kwargs):
        self.entity_source = entity_source
        super().__init__(**{
            **kwargs,
            'choices': [
                (model_field.name, model_field.verbose_name)
                for model_field in entity_source.model._meta.fields
                if isinstance(model_field, ForeignKey)
                and issubclass(model_field.related_model, CremeEntity)
                and model_field.get_tag(FieldTag.VIEWABLE)
            ],
        })

    def clean(self, value):
        field_name = super().clean(value)

        return core_workflows.EntityFKSource(
            entity_source=self.entity_source, field_name=field_name,
        ) if field_name else None

    def prepare_value(self, value):
        # TODO: if value is None?
        return value.field_name


# TODO: factorise (see RelationAddingTriggerField)
class FirstRelatedEntitySourceField(core_fields.JSONField):
    widget = RelationToCTypeSelector
    default_error_messages = {
        'rtypenotallowed': _(
            'This type of relationship does not exist or causes a constraint error'
        ),
        'forbiddenctype': _('This type of entity causes a constraint error'),
    }
    value_type = dict  # See JSONField

    def __init__(self, subject_source, **kwargs):
        super().__init__(**kwargs)
        self.subject_source = subject_source

    @property
    def subject_source(self):
        return self._subject_source

    @subject_source.setter
    def subject_source(self, source):
        self._subject_source = source
        # TODO: do not exclude a disabled rtype which is used (edition context)
        self._rtypes = rtypes = RelationType.objects.compatible(
            source.model, include_internals=True,
        ).exclude(enabled=False)
        self.widget.relation_types = core_fields.ChoiceModelIterator(
            queryset=rtypes,
        )

    def _value_from_unjsonfied(self, data):
        clean_value = self.clean_value
        ctype = self._clean_ctype(ctype_id=clean_value(data, 'ctype',  int, required=False))
        rtype = self._clean_rtype(rtype_pk=clean_value(data, 'rtype',  str))

        if not rtype.symmetric_type.is_compatible(ctype):
            raise ValidationError(
                self.error_messages['forbiddenctype'],
                code='forbiddenctype',
            )

        return core_workflows.FirstRelatedEntitySource(
            subject_source=self.subject_source,
            rtype=rtype,
            object_model=ctype.model_class(),
        )

    def _clean_rtype(self, rtype_pk):
        rtypes = self._rtypes

        try:
            rtype = rtypes.get(pk=rtype_pk)
        except rtypes.model.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['rtypenotallowed'],
                code='rtypenotallowed',
            ) from e

        return rtype

    def _value_to_jsonifiable(self, value):
        return {
            'rtype': value.relation_type.id,
            'ctype': ContentType.objects.get_for_model(value.object_model).id,
        }


class SourceField(core_fields.UnionField):
    def __init__(self, trigger=None, user=None, registry=workflow_registry, **kwargs):
        super().__init__(**kwargs)
        self.registry = registry

        self._user = user
        self.trigger = trigger

    def _update_sub_fields(self):
        user    = self._user
        trigger = self._trigger

        if trigger is None or user is None:
            self.fields_choices = []
        else:
            self.fields_choices = [
                (kind_id, field)
                for kind_id, field in self.registry.source_formfields(
                    root_sources=trigger.root_sources(), user=user,
                )
            ]

    @property
    def trigger(self):
        return self._trigger

    @trigger.setter
    def trigger(self, trigger):
        self._trigger = trigger
        self._update_sub_fields()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self._update_sub_fields()

    # TODO: improve UnionField like this + use super()?
    # def prepare_value(self, value):
    #     if value:
    #         selected_kind_id, sub_value = value
    #
    #         return selected_kind_id, {
    #             kind_id: field.prepare_value(sub_value.get(kind_id))
    #             for kind_id, field in self.fields_choices
    #         }
    def prepare_value(self, value):
        if value:
            assert isinstance(value, WorkflowSource)
            selected_kind_id = value.config_formfield_kind_id(sub_source=value.sub_source)
            field = next(
                field
                for kind_id, field in self.fields_choices
                if kind_id == selected_kind_id
            )

            return selected_kind_id, {selected_kind_id: field.prepare_value(value)}


# Forms ------------------------------------------------------------------------
class BaseWorkflowActionForm(core_forms.CremeModelForm):
    class Meta:
        model = Workflow
        fields: tuple[str, ...] = ()

    def __init__(self, action_index: int | None = None, *args, **kwargs):
        """@param action_index: Index of the edited action in the actions list
                  of the current workflow.
                  <None> means we create a new action.
        """
        super().__init__(*args, **kwargs)
        self.action_index = action_index
        self.action = None if action_index is None else self.instance.actions[action_index]

    def _build_action(self, cleaned_data) -> WorkflowAction | None:
        raise NotImplementedError

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            # NB: clean() can be called several times (with different instances
            #     of form, but referencing the same instance of Workflow), so
            #     we do not want to add the action several times.
            actions = [*self.instance.actions]
            fresh_action = self._build_action(cleaned_data=cdata)
            if (
                fresh_action is not None
                and fresh_action.to_dict() not in (action.to_dict() for action in actions)
            ):
                index = self.action_index
                if index is None:
                    actions.append(fresh_action)
                else:
                    actions[index] = fresh_action

                self.instance.actions = actions

        return cdata


class PropertyAddingActionForm(BaseWorkflowActionForm):
    source = SourceField(label=_('Entity which receives the property'))
    ptype = forms.ModelChoiceField(
        label=_('Property type'),
        queryset=CremePropertyType.objects.none(),
    )

    blocks = core_forms.FieldBlockManager({
        'id': 'general', 'label': _('Adding a property'), 'fields': '*',
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        trigger = self.instance.trigger

        source_f = fields['source']
        source_f.trigger = trigger

        ptype_f = fields['ptype']
        # TODO: do not exclude <enabled==False> if edition mode + already selected?
        ptype_f.queryset = CremePropertyType.objects.filter(enabled=True)

        action = self.action
        if action is not None:
            source_f.initial = action.entity_source
            ptype_f.initial = action.property_type.id

    def _build_action(self, cleaned_data):
        # [0] == source kind ID
        entity_source = cleaned_data['source'][1]
        ptype = cleaned_data['ptype']

        if not ptype.is_compatible(entity_source.model):
            self.add_error(
                'ptype',
                _('This property type is not compatible with the chosen type of entity.'),
            )
            return None

        return core_workflows.PropertyAddingAction(
            entity_source=entity_source, ptype=ptype,
        )


class RelationAddingActionForm(BaseWorkflowActionForm):
    subject_source = SourceField(label=_('Entity which becomes the subject'))
    rtype = forms.ModelChoiceField(
        label=_('Relationship type'),
        queryset=RelationType.objects.none(),
    )
    object_source = SourceField(label=_('Entity which becomes the object'))

    blocks = core_forms.FieldBlockManager({
        'id': 'general', 'label': _('Adding a relationship'), 'fields': '*',
    })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = self.fields
        trigger = self.instance.trigger

        subject_f = fields['subject_source']
        object_f = fields['object_source']
        rtype_f = fields['rtype']

        subject_f.trigger = trigger
        object_f.trigger = trigger
        # TODO: do not exclude <enabled==False> if edition mode + already selected?
        rtype_f.queryset = RelationType.objects.filter(enabled=True)

        action = self.action
        if action is not None:
            subject_f.initial = action.subject_source
            rtype_f.initial = action.relation_type.id
            object_f.initial = action.object_source

    def _build_action(self, cleaned_data):
        # [0] == source kind ID
        subject_source = cleaned_data['subject_source'][1]
        object_source = cleaned_data['object_source'][1]
        rtype = cleaned_data['rtype']

        if subject_source == object_source:
            self.add_error(
                None,  # Non field error
                _('You cannot use the same subject & object.'),
            )
        elif not rtype.is_compatible(subject_source.model):
            self.add_error(
                'rtype',
                _(
                    'This relationship type is not compatible with the chosen '
                    'type of subject.'
                ),
            )
        elif not rtype.symmetric_type.is_compatible(object_source.model):
            self.add_error(
                'rtype',
                _(
                    'This relationship type is not compatible with the chosen '
                    'type of object.'
                ),
            )
        else:
            return core_workflows.RelationAddingAction(
                subject_source=subject_source,
                rtype=rtype,
                object_source=object_source,
            )

        return None
