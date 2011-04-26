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
from functools import partial

from django.forms import ModelMultipleChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, EntityFilter, EntityFilterCondition, RelationType, CremePropertyType
from creme_core.forms import CremeModelForm
from creme_core.forms.fields import JSONField
from creme_core.forms.widgets import DynamicInput, SelectorList, ChainedInput, EntitySelector, UnorderedMultipleChoiceWidget
from creme_core.utils import bool_from_str
from creme_core.utils.id_generator import generate_string_id_and_save
from creme_core.utils.meta import is_date_field
from creme_core.utils.date_range import date_range_registry


TRUE = 'true'
FALSE = 'false'

_HAS_PROPERTY_OPTIONS = {
        TRUE:  _(u'Has the property'),
        FALSE: _(u'Does not have the property'),
    }

_HAS_RELATION_OPTIONS = {
        TRUE:  _(u'Has the relation'),
        FALSE: _(u'Does not have the relation'),
    }

#Form Widgets-------------------------------------------------------------------

boolean_str = lambda val: TRUE if val else FALSE


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


class DateFieldsConditionsWidget(SelectorList):
    def __init__(self, date_fields, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('name', options=[(fname, f.verbose_name) for fname, f in date_fields], attrs=attrs)
        chained_input.add_dselect('type', options=date_range_registry.choices(), attrs=attrs)

        #TODO: start  / begin

        super(DateFieldsConditionsWidget, self).__init__(chained_input)


class RelationsConditionsWidget(SelectorList):
    def __init__(self, rtypes, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        rtype_name = 'rtype'
        #ctype_url  = '/creme_core/relation/predicate/${%s}/content_types/json' % rtype_name
        ctype_url  = '/creme_core/entity_filter/rtype/${%s}/content_types' % rtype_name

        chained_input.add_dselect('has', options=_HAS_RELATION_OPTIONS.iteritems(), attrs=attrs)
        chained_input.add_dselect(rtype_name, options=rtypes, attrs=attrs)
        chained_input.add_dselect("ctype", options=ctype_url, attrs=attrs)
        chained_input.add_input("entity", widget=EntitySelector, attrs={'auto': False, 'multiple': True})

        super(RelationsConditionsWidget, self).__init__(chained_input)


class RelationSubfiltersConditionsWidget(SelectorList):
    def __init__(self, rtypes, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        rtype_name = 'rtype'
        ctype_name = 'ctype'
        ctype_url  = '/creme_core/relation/predicate/${%s}/content_types/json' % rtype_name
        filter_url = '/creme_core/entity_filter/get_for_ctype/${%s}' % ctype_name

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.iteritems(), attrs=attrs)
        add_dselect(rtype_name, options=rtypes, attrs=attrs)
        add_dselect(ctype_name, options=ctype_url, attrs=attrs)
        add_dselect("filter", options=filter_url, attrs=attrs)

        super(RelationSubfiltersConditionsWidget, self).__init__(chained_input)


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

    def initialize(self, ctype, conditions=None, efilter=None):
        self.model = ctype.model_class()

        if conditions:
            self._set_initial_conditions(conditions)


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

    def _set_initial_conditions(self, conditions):
        OPERATOR_MAP = EntityFilterCondition._OPERATOR_MAP
        self.initial = [c for c in conditions if c.type in OPERATOR_MAP]


class DateFieldsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidfield':     _(u"This field is not a date field for this model."),
        'invaliddaterange': _(u"This date range is invalid."),
    }

    def _set_model(self, model):
        self._model = model
        self._fields = dict((field.name, field) for field in model._meta.fields if is_date_field(field))
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return DateFieldsConditionsWidget(self._fields.iteritems())

    def _conditions_to_dicts(self, conditions):
        return [{'name':  condition.name,
                 'type':  condition.decoded_value['name'],
                 #'value': condition.decoded_value, #TODO start/end
                } for condition in conditions
               ]

    def _clean_date_range(self, entry):
        drange = self.clean_value(entry, 'type', str)

        if not date_range_registry.get_range(name=drange):
            raise ValidationError(self.error_messages['invaliddaterange'])

        return drange

    def _clean_field_name(self, entry):
        fname = self.clean_value(entry, 'name', str)

        if not fname in self._fields:
            raise ValidationError(self.error_messages['invalidfield'])

        return fname

    def _conditions_from_dicts(self, data):
        build_condition = EntityFilterCondition.build_4_date
        model = self.model
        clean_field_name = self._clean_field_name
        clean_date_range = self._clean_date_range

        try:
            conditions = [build_condition(model=model,
                                          name=clean_field_name(entry),
                                          date_range=clean_date_range(entry),
                                          #start=None, #TODO
                                          #end=None    #TODO
                                         )
                                for entry in data
                         ]
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        DATE = EntityFilterCondition.DATE
        self.initial = [c for c in conditions if c.type == DATE]


class RelationsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidrtype':  _(u"This relation type is invalid with this model."),
        'invalidct':     _(u"This content type is invalid."),
        'invalidentity': _(u"This entity is invalid."),
    }

    def _set_model(self, model):
        self._model = model
        self._rtypes = dict((rt.id, rt) for rt in RelationType.get_compatible_ones(ContentType.objects.get_for_model(model)))
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return RelationsConditionsWidget(self._rtypes.iteritems())

    def _condition_to_dict(self, condition):
        value = condition.decoded_value

        return {'rtype':  condition.name,
                'has':    boolean_str(value['has']),
                'ctype':  value.get('ct_id', 0),
                'entity': value.get('entity_id'),
               }

    #TODO: test with deleted entity ??
    def _conditions_to_dicts(self, conditions):
        return map(self._condition_to_dict, conditions)

    def _clean_has(self, entry):
        has = self.clean_value(entry, 'has', str)

        if has not in _HAS_RELATION_OPTIONS:
            raise ValidationError(self.error_messages['invalidformat'])

        return bool_from_str(has)

    def _clean_ct(self, entry):
        ct_id = self.clean_value(entry, 'ctype', int)

        if ct_id:
            try:
                ct = ContentType.objects.get_for_id(ct_id)
            except ContentType.DoesNotExist:
                raise ValidationError(self.error_messages['invalidct'])

            return ct

    def _clean_entity_id(self, entry):
        entity_id = entry.get('entity') #TODO: improve clean_value with default value ???

        if entity_id:
            try:
                return int(entity_id)
            except ValueError:
                raise ValidationError(self.error_messages['invalidformat'])

    def _clean_rtype(self, entry):
        rtype_id = self.clean_value(entry, 'rtype', str)
        rtype = self._rtypes.get(rtype_id)

        if not rtype:
            raise ValidationError(self.error_messages['invalidrtype'])

        return rtype

    def _conditions_from_dicts(self, data):
        all_kwargs = []
        entity_ids = set() #the queries on CremeEntity are grouped.

        for entry in data:
            kwargs = {
                        'rtype': self._clean_rtype(entry),
                        'has':   self._clean_has(entry),
                        'ct':    self._clean_ct(entry),
                     }
            entity_id = self._clean_entity_id(entry)

            if entity_id:
                entity_ids.add(entity_id)
                kwargs['entity'] = entity_id

            all_kwargs.append(kwargs)

        if entity_ids:
            entities = dict((e.id, e) for e in CremeEntity.objects.filter(pk__in=entity_ids))

            if len(entities) != len(entity_ids):
                raise ValidationError(self.error_messages['invalidentity'])

            for kwargs in all_kwargs:
                kwargs['entity'] = entities.get(kwargs['entity'])

        build_condition = EntityFilterCondition.build_4_relation

        try:
            conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        RELATION = EntityFilterCondition.RELATION
        self.initial = [c for c in conditions if c.type == RELATION]


class RelationSubfiltersConditionsField(RelationsConditionsField):
    default_error_messages = {
        'invalidfilter': _(u"This filter is invalid."),
    }

    def _create_widget(self):
        return RelationSubfiltersConditionsWidget(self._rtypes.iteritems())

    def _condition_to_dict(self, condition):
        value = condition.decoded_value

        return {'rtype':  condition.name,
                'has':    boolean_str(value['has']),
                'filter': value['filter_id'],
               }

    def _conditions_from_dicts(self, data):
        all_kwargs = []
        filter_ids = set() #the queries on EntityFilter are grouped.

        for entry in data:
            kwargs    = {'rtype': self._clean_rtype(entry), 'has': self._clean_has(entry)}
            filter_id = self.clean_value(entry, 'filter', str)

            if filter_id:
                filter_ids.add(filter_id)
                kwargs['subfilter'] = filter_id

            all_kwargs.append(kwargs)

        if filter_ids:
            filters = dict((f.id, f) for f in EntityFilter.objects.filter(pk__in=filter_ids))

            if len(filters) != len(filter_ids):
                raise ValidationError(self.error_messages['invalidfilter'])

            for kwargs in all_kwargs:
                kwargs['subfilter'] = filters.get(kwargs['subfilter'])

        build_condition = EntityFilterCondition.build_4_relation_subfilter

        try:
             conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        RELATION_SUBFILTER = EntityFilterCondition.RELATION_SUBFILTER
        self.initial = [c for c in conditions if c.type == RELATION_SUBFILTER]


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
        return [{'ptype': condition.name,
                 'has':   boolean_str(condition.decoded_value),
                } for condition in conditions
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

    def _set_initial_conditions(self, conditions):
        PROPERTY = EntityFilterCondition.PROPERTY
        self.initial = [c for c in conditions if c.type == PROPERTY]


class SubfiltersConditionsField(ModelMultipleChoiceField):
    widget = UnorderedMultipleChoiceWidget

    def __init__(self, model=None, *args, **kwargs):
        super(SubfiltersConditionsField, self).__init__(queryset=EntityFilter.objects.none(), *args, **kwargs)
        self.model = model or CremeEntity #TODO: remove

    def clean(self, value):
        subfilters = super(SubfiltersConditionsField, self).clean(value)
        build_cond = partial(EntityFilterCondition.build, type=EntityFilterCondition.SUBFILTER, model=self.model)

        return [build_cond(value=subfilter) for subfilter in subfilters]

    def initialize(self, ctype, conditions=None, efilter=None):
        qs = EntityFilter.objects.filter(entity_type=ctype)

        if efilter:
            qs = qs.exclude(pk__in=efilter.get_connected_filter_ids())

        self.queryset = qs

        if conditions:
            SUBFILTER = EntityFilterCondition.SUBFILTER
            self.initial = [c.decoded_value for c in conditions if c.type == SUBFILTER]


#Forms--------------------------------------------------------------------------

class _EntityFilterForm(CremeModelForm):
    fields_conditions        = RegularFieldsConditionsField(label=_(u'On regular fields'), required=False)
    datefields_conditions    = DateFieldsConditionsField(label=_(u'On date fields'), required=False)
    relations_conditions     = RelationsConditionsField(label=_(u'On relations'), required=False,
                                                        help_text=_(u'Do not select any entity if you want to match them all.')
                                                       )
    relsubfilfers_conditions = RelationSubfiltersConditionsField(label=_(u'On relations with results of other filters'), required=False)
    properties_conditions    = PropertiesConditionsField(label=_(u'On properties'), required=False)
    subfilters_conditions    = SubfiltersConditionsField(label=_(u'Sub-filters'), required=False)

    _CONDITIONS_FIELD_NAMES = ('fields_conditions', 'datefields_conditions',
                               'relations_conditions', 'relsubfilfers_conditions',
                               'properties_conditions', 'subfilters_conditions',
                             )

    blocks = CremeModelForm.blocks.new(('conditions', _(u'Conditions'), _CONDITIONS_FIELD_NAMES))

    class Meta:
        model = EntityFilter

    def __init__(self, *args, **kwargs):
        super(_EntityFilterForm, self).__init__(*args, **kwargs)
        fields = self.fields
        fields['user'].empty_label = ugettext(u'All users')
        fields['use_or'].help_text = ugettext(u'Use "OR" between the conditions (else "AND" is used).')

    def get_cleaned_conditions(self):
        cdata = self.cleaned_data
        conditions = []

        for fname in self._CONDITIONS_FIELD_NAMES:
            conditions.extend(cdata[fname])

        return conditions

    def clean(self):
        cdata = self.cleaned_data

        #TODO: get fields names from the block instead ??
        if not self._errors and not any(cdata[f] for f in self._CONDITIONS_FIELD_NAMES):
            raise ValidationError(ugettext(u'The filter must have at least one condition.'))

        return cdata


class EntityFilterCreateForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterCreateForm, self).__init__(*args, **kwargs)
        self._entity_type = ct = self.initial['content_type']
        fields = self.fields

        for field_name in self._CONDITIONS_FIELD_NAMES:
            fields[field_name].initialize(ct)

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        instance.is_custom = True
        instance.entity_type = ct

        super(EntityFilterCreateForm, self).save(commit=False, *args, **kwargs)
        generate_string_id_and_save(EntityFilter, [instance], 'creme_core-userfilter_%s-%s' % (ct.app_label, ct.model))

        instance.set_conditions(self.get_cleaned_conditions(), check_cycles=False)

        return instance


class EntityFilterEditForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance
        args = (instance.entity_type, instance.conditions.all(), instance)

        for field_name in self._CONDITIONS_FIELD_NAMES:
            fields[field_name].initialize(*args)

    def clean(self):
        cdata = super(EntityFilterEditForm, self).clean()

        if not self.errors:
            conditions = self.get_cleaned_conditions()

            try:
                self.instance.check_cycle(conditions)
            except EntityFilter.CycleError, e:
                 raise ValidationError(e)

            cdata['all_conditions'] = conditions

        return cdata

    def save(self, *args, **kwargs):
        instance = super(EntityFilterEditForm, self).save(*args, **kwargs)
        instance.set_conditions(self.cleaned_data['all_conditions'], check_cycles=False)

        return instance
