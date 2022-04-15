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

from creme.creme_config.forms.workflow import SourceField
from creme.creme_core import forms as core_forms
from creme.creme_core import workflows as core_workflows
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.core.workflow import WorkflowAction
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
class EntityCreationTriggerField(forms.Field):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core.workflows import EntityCreationTrigger
        return EntityCreationTrigger(model=self.model)


# TODO: factorise
class EntityEditionTriggerField(forms.CharField):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core.workflows import EntityEditionTrigger
        return EntityEditionTrigger(model=self.model)


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
        from creme.creme_core.workflows import RelationAddingTrigger

        clean_value = self.clean_value
        ctype = self._clean_ctype(ctype_id=clean_value(data, 'ctype',  int, required=False))
        rtype = self._clean_rtype(rtype_pk=clean_value(data, 'rtype',  str))

        if not rtype.symmetric_type.is_compatible(ctype):
            raise ValidationError(
                self.error_messages['forbiddenctype'],
                code='forbiddenctype',
            )

        return RelationAddingTrigger(
            subject_model=self._model,
            rtype=rtype,
            # TODO: accept ContentType too?
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


class CreatedEntitySourceField(forms.Field):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core import workflows
        return workflows.CreatedEntitySource(model=self.model)


# TODO: factorise
class EditedEntitySourceField(forms.Field):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core import workflows
        return workflows.EditedEntitySource(model=self.model)


# TODO: factorise
class SubjectEntitySourceField(forms.Field):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core import workflows
        return workflows.SubjectEntitySource(model=self.model)


# TODO: factorise
class ObjectEntitySourceField(forms.Field):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core import workflows
        return workflows.ObjectEntitySource(model=self.model)


class FixedEntitySourceField(core_fields.GenericEntityField):
    def __init__(self, **kwargs):
        # TODO: test credentials
        super().__init__(**{
            **kwargs,
            'required': False,
            'credentials': EntityCredentials.VIEW,
        })

    def clean(self, value):
        from creme.creme_core import workflows

        entity = super().clean(value)

        return workflows.FixedEntitySource(entity=entity) if entity else None


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
        from creme.creme_core import workflows

        field_name = super().clean(value)

        return workflows.EntityFKSource(
            entity_source=self.entity_source,
            field_name=field_name,
        ) if field_name else None


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
        from creme.creme_core.workflows import FirstRelatedEntitySource

        clean_value = self.clean_value
        ctype = self._clean_ctype(ctype_id=clean_value(data, 'ctype',  int, required=False))
        rtype = self._clean_rtype(rtype_pk=clean_value(data, 'rtype',  str))

        if not rtype.symmetric_type.is_compatible(ctype):
            raise ValidationError(
                self.error_messages['forbiddenctype'],
                code='forbiddenctype',
            )

        return FirstRelatedEntitySource(
            subject_source=self.subject_source,
            rtype=rtype,
            # TODO: accept ContentType too?
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


class BaseWorkflowActionForm(core_forms.CremeModelForm):
    class Meta:
        model = Workflow
        fields: tuple[str, ...] = ()

    def _build_action(self, cleaned_data) -> WorkflowAction | None:
        raise NotImplementedError

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            # NB: clean() can be called several times (with different instances
            #     of form, but referencing the same instance of Workflow), so
            #     we do not want to add the action several times.
            actions = self.instance.actions
            new_action = self._build_action(cleaned_data=cdata)
            if (
                new_action is not None
                and new_action.to_dict() not in (action.to_dict() for action in actions)
            ):
                actions.append(new_action)
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
        fields['source'].trigger = trigger
        # TODO: do not exclude <enabled==False> if edition mode + already selected?
        fields['ptype'].queryset = CremePropertyType.objects.filter(enabled=True)

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
        fields['subject_source'].trigger = trigger
        fields['object_source'].trigger = trigger
        # TODO: do not exclude <enabled==False> if edition mode + already selected?
        fields['rtype'].queryset = RelationType.objects.filter(enabled=True)

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
