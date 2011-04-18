# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

#from logging import debug

from django.forms import ModelMultipleChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, EntityFilter, EntityFilterCondition, CremePropertyType
from creme_core.forms import CremeModelForm
from creme_core.forms.fields import JSONField
from creme_core.forms.widgets import DynamicInput, SelectorList, ChainedInput, UnorderedMultipleChoiceWidget
from creme_core.utils import bool_from_str
from creme_core.utils.id_generator import generate_string_id_and_save
from creme_core.utils.meta import is_date_field


_HAS_PROPERTY_OPTIONS = {
        'true':  _(u'Has'),
        'false': _(u'Does not have'),
    }


#Form Widgets-------------------------------------------------------------------

class RegularFieldsConditionsWidget(SelectorList):
    def __init__(self, model, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        excluded = model.header_filter_exclude_fields
        model_fields = [(f.name, f.verbose_name) for f in model._meta.fields #TODO: move to field ???
                            if f.name not in excluded and
                               not is_date_field(f) and
                               not f.get_internal_type() == 'ForeignKey'
                       ]

        chained_input.add_dselect('name', options=model_fields, attrs=attrs)
        chained_input.add_dselect('type', options=EntityFilterCondition._OPERATOR_MAP.iteritems(), attrs=attrs)
        chained_input.add_input('value', DynamicInput, attrs=attrs)

        super(RegularFieldsConditionsWidget, self).__init__(chained_input)


class PropertiesConditionsWidget(SelectorList):
    def __init__(self, ptypes, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('has', options=_HAS_PROPERTY_OPTIONS.iteritems(), attrs=attrs)
        chained_input.add_dselect('ptype', options=ptypes, attrs=attrs)

        super(PropertiesConditionsWidget, self).__init__(chained_input)


#Form Fields--------------------------------------------------------------------

class _ConditionsField(JSONField):
    def __init__(self, model=None, *args, **kwargs):
        super(_ConditionsField, self).__init__(*args, **kwargs)
        self.model = model or CremeEntity

    def _conditions_to_dicts(self, conditions):
        raise NotImplementedError

    def _conditions_from_dicts(self, data):
        raise NotImplementedError

    def from_python(self, value):
        if not value:
            return ''

        if isinstance(value, basestring):
            return value

        return self.format_json(self._conditions_to_dicts(value))

    def clean(self, value):
        data = self.clean_json(value)

        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return []

        return self._conditions_from_dicts(data)


class RegularFieldsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidfield': _(u"This field is invalid with this model."),
    }

    def _set_model(self, model):
        self._model = model
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model #TODO: lazy_property

    def _create_widget(self):
        return RegularFieldsConditionsWidget(self.model)

    def _conditions_to_dicts(self, conditions):
        return [{'type':  condition.type,
                 'name':  condition.name,
                 'value': condition.decoded_value,
                } for condition in conditions
               ]

    def _conditions_from_dicts(self, data):
        build_condition = EntityFilterCondition.build
        clean_value = self.clean_value

        try:
            conditions = [build_condition(model=self.model,
                                          type=clean_value(entry, 'type', int),
                                          name=clean_value(entry, 'name', str),
                                          value=clean_value(entry, 'value', unicode),
                                         )
                                for entry in data
                         ]
        except EntityFilterCondition.ValueError:
            raise ValidationError(self.error_messages['invalidfield'])

        return conditions


class PropertiesConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidptype': _(u"This property type is invalid with this model."),
    }

    def _set_model(self, model):
        self._model = model
        self._ptypes = dict((pt.id, pt) for pt in CremePropertyType.get_compatible_ones(ContentType.objects.get_for_model(model)))
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return PropertiesConditionsWidget(self._ptypes.iteritems())

    def _conditions_to_dicts(self, conditions):
        return [{'ptype':  condition.name,
                 'has': 'true' if condition.decoded_value else 'false' #TODO: const ??,
                } for condition in value
               ]

    def _clean_has(self, entry):
        has = self.clean_value(entry, 'has', str)

        if has not in _HAS_PROPERTY_OPTIONS:
            raise ValidationError(self.error_messages['invalidformat'])

        return bool_from_str(has)

    def _clean_ptype(self, entry):
        ptype_id = self.clean_value(entry, 'ptype', str)

        if ptype_id not in self._ptypes:
            raise ValidationError(self.error_messages['invalidptype'])

        return ptype_id

    def _conditions_from_dicts(self, data):
        build_condition = EntityFilterCondition.build
        clean_has   = self._clean_has
        clean_ptype = self._clean_ptype

        try:
            conditions = [build_condition(model=self.model,
                                          type=EntityFilterCondition.PROPERTY,
                                          name=clean_ptype(entry),
                                          value=clean_has(entry),
                                         )
                                for entry in data
                         ]
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

#Forms--------------------------------------------------------------------------

class _EntityFilterForm(CremeModelForm):
    fields_conditions     = RegularFieldsConditionsField(label=_(u'On regular fields'), required=False)
    properties_conditions = PropertiesConditionsField(label=_(u'On properties'), required=False)
    subfilters_conditions = ModelMultipleChoiceField(label=_(u'Sub-filters'), required=False,
                                                     queryset=EntityFilter.objects.none(),
                                                     widget=UnorderedMultipleChoiceWidget)

    blocks = CremeModelForm.blocks.new(('conditions', _(u'Conditions'), ('fields_conditions',
                                                                         'properties_conditions',
                                                                         'subfilters_conditions',
                                                                        )
                                      ))

    class Meta:
        model = EntityFilter

    def __init__(self, *args, **kwargs):
        super(_EntityFilterForm, self).__init__(*args, **kwargs)
        fields = self.fields
        fields['user'].empty_label = ugettext(u'All users')
        fields['use_or'].help_text = ugettext(u'Use "OR" between the conditions (else "AND" is used).')

    def _build_subfilters(self, model):
        build_cond = EntityFilterCondition.build
        SUBFILTER = EntityFilterCondition.SUBFILTER

        return [build_cond(model=model, type=SUBFILTER, value=subfilter)
                     for subfilter in self.cleaned_data['subfilters_conditions']
               ]

    def set_conditions(self):
        efilter = self.instance
        efilter.set_conditions(self.cleaned_data['fields_conditions']
                                + self.cleaned_data['properties_conditions']
                                + self._build_subfilters(efilter.entity_type.model_class()),
                               check_cycles=False
                              )

    def clean(self):
        cdata = self.cleaned_data

        if not any(cdata[f] for f in ('fields_conditions', 'subfilters_conditions', 'properties_conditions')):
            raise ValidationError(ugettext(u'The filter must have at least one condition.'))

        return cdata


class EntityFilterCreateForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterCreateForm, self).__init__(*args, **kwargs)
        ct = self.initial['content_type']
        self._entity_type = ct #TODO: remove this attr ??

        fields = self.fields
        model = ct.model_class()
        fields['fields_conditions'].model = model
        fields['properties_conditions'].model = model
        fields['subfilters_conditions'].queryset = EntityFilter.objects.filter(entity_type=ct)

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        instance.is_custom = True
        instance.entity_type = ct

        super(EntityFilterCreateForm, self).save(commit=False, *args, **kwargs)
        generate_string_id_and_save(EntityFilter, [instance], 'creme_core-userfilter_%s-%s' % (ct.app_label, ct.model))

        self.set_conditions()

        return instance


class EntityFilterEditForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance
        ct = instance.entity_type
        model = ct.model_class()
        conditions = instance.conditions.all()

        OPERATOR_MAP = EntityFilterCondition._OPERATOR_MAP
        f_conditions_field = fields['fields_conditions']
        f_conditions_field.model   = model
        f_conditions_field.initial = [c for c in conditions if c.type in OPERATOR_MAP]

        PROPERTY = EntityFilterCondition.PROPERTY
        p_conditions_field = fields['properties_conditions']
        p_conditions_field.model = model
        p_conditions_field.initial = [c for c in conditions if c.type == PROPERTY]

        SUBFILTER = EntityFilterCondition.SUBFILTER
        sf_conditions_field = fields['subfilters_conditions']
        sf_conditions_field.queryset = EntityFilter.objects.filter(entity_type=ct)\
                                                           .exclude(pk__in=instance.get_connected_filter_ids())
        sf_conditions_field.initial = [c.decoded_value for c in conditions if c.type == SUBFILTER]

    def save(self, *args, **kwargs):
        instance = super(EntityFilterEditForm, self).save(*args, **kwargs)
        self.set_conditions()

        return instance
