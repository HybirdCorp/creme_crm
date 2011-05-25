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

from collections import defaultdict
from datetime import date

from django.forms import ModelMultipleChoiceField, DateField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.formats import date_format
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeEntity, EntityFilter, EntityFilterCondition, RelationType, CremePropertyType, CustomField
from creme_core.models.entity_filter import _ConditionBooleanOperator

from creme_core.forms import CremeModelForm
from creme_core.forms.fields import JSONField
from creme_core.forms.widgets import DynamicInput, SelectorList, ChainedInput, EntitySelector, UnorderedMultipleChoiceWidget, DateRangeSelect, DynamicSelect, PolymorphicInput
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

_CONDITION_INPUT_TYPE_MAP = {
        _ConditionBooleanOperator: (DynamicSelect,
                                    {'auto': False},
                                    {'options': ((TRUE, _("True")), (FALSE, _("False")))}),
    }

#Form Widgets-------------------------------------------------------------------

boolean_str = lambda val: TRUE if val else FALSE


class RegularFieldsConditionsWidget(SelectorList):
    def __init__(self, fields, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('name',     options=self._build_fieldchoices(fields), attrs=attrs)
        chained_input.add_dselect('operator', options=EntityFilterCondition._OPERATOR_MAP.iteritems(), attrs=attrs)

        pinput = PolymorphicInput(url='${operator}', attrs=attrs)
        pinput.set_default_input(widget=DynamicInput, attrs=attrs)

        for optype, operator in EntityFilterCondition._OPERATOR_MAP.iteritems():
            op_input = _CONDITION_INPUT_TYPE_MAP.get(type(operator))

            if op_input:
                input_widget, input_attrs, input_kwargs = op_input
                pinput.add_input(str(optype), widget=input_widget, attrs=input_attrs, **input_kwargs)

        chained_input.add_input('value', pinput, attrs=attrs)

        super(RegularFieldsConditionsWidget, self).__init__(chained_input)

    def _build_fieldchoices(self, fields):
        fields_by_cat = defaultdict(list) #fields grouped by category (a category by FK)

        for fname, fieldlist in fields.iteritems():
            key = '' if len(fieldlist) == 1 else unicode(fieldlist[0].verbose_name) # == 1 -> not a FK
            fields_by_cat[key].append((fname, fieldlist[-1].verbose_name))

        return [(cat, sorted(fields_by_cat[cat], key=lambda item: item[1]))
                    for cat in sorted(fields_by_cat.keys())
               ]


class DateFieldsConditionsWidget(SelectorList):
    def __init__(self, date_fields_options, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('field', options=date_fields_options, attrs=attrs)
        chained_input.add_input('range', DateRangeSelect, attrs=attrs)

        super(DateFieldsConditionsWidget, self).__init__(chained_input)


class CustomFieldsConditionsWidget(SelectorList): #TODO: factorise with RegularFieldsConditionsWidget ???
    def __init__(self, cfields, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('field',    options=cfields.iteritems(), attrs=attrs)
        chained_input.add_dselect('operator', options=EntityFilterCondition._OPERATOR_MAP.iteritems(), attrs=attrs)
        chained_input.add_input('value', DynamicInput, attrs=attrs)

        super(CustomFieldsConditionsWidget, self).__init__(chained_input)


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
        'invalidfield':    _(u"This field is invalid with this model."),
        'invalidoperator': _(u"This operator is invalid."),
    }

    def _build_related_fields(self, field, fields):
        fname = field.name
        related_model = field.rel.to
        rel_excluded = set(related_model.header_filter_exclude_fields if issubclass(related_model, CremeEntity) else
                           ('id',)
                          )

        for subfield in related_model._meta.fields:
            sfname = subfield.name

            if sfname not in rel_excluded and not is_date_field(subfield):
                fields['%s__%s' % (fname, sfname)] =  [field, subfield]

    def _set_model(self, model):
        self._model = model
        self._fields = fields = {}

        excluded = model.header_filter_exclude_fields

        #TODO: move code in meta.utils (and use in HeaderFilter for example) ??
        for field in model._meta.fields:
            fname = field.name

            if fname not in excluded and not is_date_field(field):
               if field.get_internal_type() == 'ForeignKey':
                    self._build_related_fields(field, fields)
               else:
                   fields[fname] = [field]

        for field in model._meta.many_to_many:
            self._build_related_fields(field, fields)

        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model #TODO: lazy_property

    def _create_widget(self):
        return RegularFieldsConditionsWidget(self._fields)

    def _conditions_to_dicts(self, conditions):
        dicts = []

        for condition in conditions:
            search_info = condition.decoded_value
            operator = search_info['operator']

            #TODO: use polymorphism instead ??
            if isinstance(EntityFilterCondition._OPERATOR_MAP.get(operator), _ConditionBooleanOperator):
                values = search_info['values'][0]
            else:
                values = u','.join(search_info['values'])

            dicts.append({'operator': operator,
                          'name':     condition.name,
                          'value':    {'type': operator, 'value': values},
                         })

        return dicts

    def _clean_fieldname(self, entry):
        fname = self.clean_value(entry, 'name', str)

        if fname not in self._fields:
            raise ValidationError(self.error_messages['invalidfield'])

        return fname

    def _clean_operator_n_values(self, entry):
        clean_value =  self.clean_value
        operator = self.clean_value(entry, 'operator', int)

        operator_class = EntityFilterCondition._OPERATOR_MAP.get(operator)
        if not operator_class:
            raise ValidationError(self.error_messages['invalidoperator'])

        value_dict = clean_value(entry, 'value', dict)

        if isinstance(operator_class, _ConditionBooleanOperator):
            values = [clean_value(value_dict, 'value', bool)]
        else:
            values = filter(None, clean_value(value_dict, 'value', unicode).split(','))

        return operator, values

    def _conditions_from_dicts(self, data):
        build_4_field = EntityFilterCondition.build_4_field
        clean_fieldname = self._clean_fieldname
        clean_operator_n_values = self._clean_operator_n_values

        try:
            conditions = []

            for entry in data:
                operator, values = clean_operator_n_values(entry)
                conditions.append(build_4_field(model=self.model, name=clean_fieldname(entry),
                                                operator=operator, values=values
                                               )
                                 )
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        FIELD = EntityFilterCondition.EFC_FIELD
        self.initial = [c for c in conditions if c.type == FIELD]


class DateFieldsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidfield':     _(u"This field is not a date field for this model."),
        'invaliddaterange': _(u"This date range is invalid."),
        'emptydates':       _(u"Please enter a start date and/or a end date."),
    }

    def _set_model(self, model):
        self._model = model
        self._fields = dict((field.name, field) for field in model._meta.fields if is_date_field(field))
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return DateFieldsConditionsWidget([(fname, f.verbose_name) for fname, f in self._fields.iteritems()])

    def _format_date(self, date_dict):
        """@param date_dict dict or None; if not None => {"year": 2011, "month": 7, "day": 25}"""
        return date_format(date(**date_dict), 'DATE_FORMAT') if date_dict else ''

    def _conditions_to_dicts(self, conditions):
        dicts = []
        format = self._format_date

        for condition in conditions:
            get = condition.decoded_value.get

            dicts.append({'field':  condition.name,
                          'range': {'type':  get('name', ''),
                                    'start': format(get('start')),
                                    'end':   format(get('end'))
                                   }
                         })

        return dicts

    def _clean_date_range(self, entry):
        range_info = entry.get('range')

        if not isinstance(range_info, dict):
            raise ValidationError(self.error_messages['invalidformat'])

        range_type = range_info.get('type') or None
        start = None
        end   = None

        if not range_type:
            start_str = range_info.get('start')
            end_str   = range_info.get('end')

            if not start_str and not end_str:
                raise ValidationError(self.error_messages['emptydates'])

            clean_date = DateField().clean

            if start_str:
                start = clean_date(start_str)

            if end_str:
                end = clean_date(end_str)
        elif not date_range_registry.get_range(name=range_type):
            raise ValidationError(self.error_messages['invaliddaterange'])

        return (range_type, start, end)

    def _clean_field_name(self, entry):
        fname = self.clean_value(entry, 'field', str)

        if not fname in self._fields:
            raise ValidationError(self.error_messages['invalidfield'])

        return fname

    def _conditions_from_dicts(self, data):
        build_condition = EntityFilterCondition.build_4_date
        model = self.model
        clean_field_name = self._clean_field_name
        clean_date_range = self._clean_date_range
        conditions = []

        try:
            for entry in data:
                date_range, start, end = clean_date_range(entry)
                conditions.append(build_condition(model=model, name=clean_field_name(entry),
                                                  date_range=date_range, start=start, end=end
                                                 )
                                 )
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        DATE = EntityFilterCondition.EFC_DATEFIELD
        self.initial = [c for c in conditions if c.type == DATE]


class CustomFieldsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidcustomfield': _(u"This custom field is invalid with this model."),
        'invalidtype':        _(u"This operator is invalid."),
    }

    _ACCEPTED_TYPES = frozenset((CustomField.INT, CustomField.FLOAT, CustomField.STR)) #TODO: "!= DATE" instead

    def _set_model(self, model):
        self._model = model
        self._cfields = dict((cf.id, cf) for cf in CustomField.objects.filter(content_type=ContentType.objects.get_for_model(model),
                                                                              field_type__in=self._ACCEPTED_TYPES
                                                                             )
                            )
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return CustomFieldsConditionsWidget(self._cfields)

    def _conditions_to_dicts(self, conditions):
        dicts = []

        for condition in conditions:
            search_info = condition.decoded_value
            dicts.append({'field':    condition.name,
                          'operator': search_info['operator'],
                          'value':    search_info['value'],
                         })

        return dicts

    def _clean_custom_field(self, entry):
        cfield_id = self.clean_value(entry, 'field', int)
        cf = self._cfields.get(cfield_id)

        if not cf:
            raise ValidationError(self.error_messages['invalidcustomfield'])

        return cf

    def _conditions_from_dicts(self, data):
        build_condition = EntityFilterCondition.build_4_customfield
        clean_value = self.clean_value
        clean_cfield = self._clean_custom_field

        try:
            conditions = [build_condition(custom_field=clean_cfield(entry),
                                          operator=clean_value(entry, 'operator', int), #TODO: 'invalidoperator'
                                          value=clean_value(entry, 'value', unicode)
                                         ) for entry in data
                         ]
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(self.error_messages['invalidtype'])

        return conditions

    def _set_initial_conditions(self, conditions):
        CUSTOMFIELD = EntityFilterCondition.EFC_CUSTOMFIELD
        self.initial = [c for c in conditions if c.type == CUSTOMFIELD]


class DateCustomFieldsConditionsField(CustomFieldsConditionsField, DateFieldsConditionsField):
    default_error_messages = {
        'invalidcustomfield': _(u"This date custom field is invalid with this model."),
    }

    def _set_model(self, model):
        self._model = model
        self._cfields = dict((cf.id, cf) for cf in CustomField.objects.filter(content_type=ContentType.objects.get_for_model(model),
                                                                              field_type=CustomField.DATE
                                                                             )
                            )
        self._build_widget()

    model = property(lambda self: self._model, _set_model); del _set_model

    def _create_widget(self):
        return DateFieldsConditionsWidget(self._cfields.iteritems())

    def _conditions_to_dicts(self, conditions):
        return DateFieldsConditionsField._conditions_to_dicts(self, conditions)

    def _conditions_from_dicts(self, data):
        build_condition = EntityFilterCondition.build_4_datecustomfield
        clean_cfield = self._clean_custom_field
        clean_date_range = self._clean_date_range
        conditions = []

        try:
            for entry in data:
                date_range, start, end = clean_date_range(entry)
                conditions.append(build_condition(custom_field=clean_cfield(entry),
                                                  date_range=date_range, start=start, end=end
                                                 )
                                 )
        except EntityFilterCondition.ValueError, e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        DATECUSTOMFIELD = EntityFilterCondition.EFC_DATECUSTOMFIELD
        self.initial = [c for c in conditions if c.type == DATECUSTOMFIELD]


class RelationsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidrtype':  _(u"This relation type is invalid with this model."),
        'invalidct':     _(u"This content type is invalid."),
        'invalidentity': _(u"This entity is invalid."),
    }

    def _set_model(self, model):
        self._model = model
        self._rtypes = dict((rt.id, rt) for rt in RelationType.get_compatible_ones(ContentType.objects.get_for_model(model), include_internals=True))
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
                        'has':   self.clean_value(entry, 'has', bool),
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
        RELATION = EntityFilterCondition.EFC_RELATION
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
            kwargs    = {'rtype': self._clean_rtype(entry), 'has': self.clean_value(entry, 'has', bool)}
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
        RELATION_SUBFILTER = EntityFilterCondition.EFC_RELATION_SUBFILTER
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

    def _clean_ptype(self, entry):
        ptype = self._ptypes.get(self.clean_value(entry, 'ptype', str))

        if not ptype:
            raise ValidationError(self.error_messages['invalidptype'])

        return ptype

    def _conditions_from_dicts(self, data):
        build = EntityFilterCondition.build_4_property
        clean_ptype = self._clean_ptype
        clean_value = self.clean_value

        return [build(ptype=clean_ptype(entry), has=clean_value(entry, 'has', bool)) for entry in data]

    def _set_initial_conditions(self, conditions):
        PROPERTY = EntityFilterCondition.EFC_PROPERTY
        self.initial = [c for c in conditions if c.type == PROPERTY]


class SubfiltersConditionsField(ModelMultipleChoiceField):
    widget = UnorderedMultipleChoiceWidget

    def __init__(self, model=None, *args, **kwargs):
        super(SubfiltersConditionsField, self).__init__(queryset=EntityFilter.objects.none(), *args, **kwargs)
        self.model = model or CremeEntity #TODO: remove

    def clean(self, value):
        build = EntityFilterCondition.build_4_subfilter

        return [build(subfilter) for subfilter in super(SubfiltersConditionsField, self).clean(value)]

    def initialize(self, ctype, conditions=None, efilter=None):
        qs = EntityFilter.objects.filter(entity_type=ctype)

        if efilter:
            qs = qs.exclude(pk__in=efilter.get_connected_filter_ids())

        self.queryset = qs

        if conditions:
            SUBFILTER = EntityFilterCondition.EFC_SUBFILTER
            self.initial = [c.name for c in conditions if c.type == SUBFILTER]


#Forms--------------------------------------------------------------------------

class _EntityFilterForm(CremeModelForm):
    fields_conditions           = RegularFieldsConditionsField(label=_(u'On regular fields'), required=False,
                                                               help_text=_(u'You can write several values, separated by commas.')
                                                              )
    datefields_conditions       = DateFieldsConditionsField(label=_(u'On date fields'), required=False)
    customfields_conditions     = CustomFieldsConditionsField(label=_(u'On custom fields'), required=False, help_text=u'(Only integer, string and decimal for now)')
    datecustomfields_conditions = DateCustomFieldsConditionsField(label=_(u'On date custom fields'), required=False)
    relations_conditions        = RelationsConditionsField(label=_(u'On relations'), required=False,
                                                           help_text=_(u'Do not select any entity if you want to match them all.')
                                                          )
    relsubfilfers_conditions    = RelationSubfiltersConditionsField(label=_(u'On relations with results of other filters'), required=False)
    properties_conditions       = PropertiesConditionsField(label=_(u'On properties'), required=False)
    subfilters_conditions       = SubfiltersConditionsField(label=_(u'Sub-filters'), required=False)

    _CONDITIONS_FIELD_NAMES = ('fields_conditions', 'datefields_conditions',
                               'customfields_conditions', 'datecustomfields_conditions',
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
