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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms import widgets as core_widgets
from creme.creme_core.models import CremePropertyType, RelationType
from creme.creme_core.utils.url import TemplateURLBuilder


# Widgets ----------------------------------------------------------------------
class RelationAddingTriggerWidget(core_widgets.ChainedInput):
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
    widget = RelationAddingTriggerWidget
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
        rtype_pk = clean_value(data, 'rtype',  str)

        ctype_pk = clean_value(data, 'ctype',  int, required=False)
        if not ctype_pk:
            return self._return_none_or_raise(self.required, 'ctyperequired')

        # TODO: use super()._clean_ctype() when is exist
        try:
            ctype = ContentType.objects.get_for_id(ctype_pk)
        except ContentType.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['ctypenotallowed'],
                code='ctypenotallowed',
            ) from e

        rtype = self._clean_rtype(rtype_pk)
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


# TODO: test
# TODO: remove/rework (produce descriptor instead of source)
class CreatedEntitySourceField(forms.Field):
    widget = forms.HiddenInput

    def __init__(self, model, **kwargs):
        super().__init__(**{**kwargs, 'required': False})
        self.model = model

    def to_python(self, value):
        from creme.creme_core import workflows
        return workflows._FromContextSource(
            context_key=workflows.EntityCreationTrigger.CREATED,
        )


class PropertyAddingActionField(forms.ModelChoiceField):
    # widget = forms.HiddenInput

    # TODO: "sourcss"
    def __init__(self, source, **kwargs):
        super().__init__(queryset=CremePropertyType.objects.all())
        self.source = source

    def to_python(self, value):
        from creme.creme_core.workflows import PropertyAddingAction

        ptype = super().to_python(value=value)

        # TODO: if None
        return PropertyAddingAction(entity_source=self.source, ptype=ptype)
