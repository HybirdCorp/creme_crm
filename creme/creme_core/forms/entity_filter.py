# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from future_builtins import map
from collections import defaultdict
from datetime import date
import json

from django.db.models import (ForeignKey as ModelForeignKey, DateField as ModelDateField,
        IntegerField as ModelIntegerField, FloatField as ModelFloatField,
        DecimalField as ModelDecimalField, BooleanField as ModelBooleanField)
from django.forms import ModelMultipleChoiceField, DateField, ChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.formats import date_format
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from ..models import (CremeEntity, EntityFilter, EntityFilterCondition,
        RelationType, CremePropertyType, CustomField)
from ..models.entity_filter import _ConditionBooleanOperator, _IsEmptyOperator
from ..utils.id_generator import generate_string_id_and_save
from ..utils.meta import is_date_field
from ..utils.date_range import date_range_registry
from ..utils.unicode_collation import collator
from .base import CremeModelForm
from .fields import JSONField
from .widgets import (Label, DynamicInput, SelectorList, ChainedInput,
        EntitySelector, UnorderedMultipleChoiceWidget, DateRangeSelect,
        DynamicSelect, PolymorphicInput, CremeRadioSelect)


TRUE = 'true'
FALSE = 'false'

_HAS_PROPERTY_OPTIONS = {
        TRUE:  _(u'Has the property'),
        FALSE: _(u'Does not have the property'),
    }

_HAS_RELATION_OPTIONS = {
        TRUE:  _(u'Has the relationship'),
        FALSE: _(u'Does not have the relationship'),
    }

_CONDITION_INPUT_TYPE_MAP = {
        _ConditionBooleanOperator: (DynamicSelect,
                                    {'auto': False},
                                    {'options': ((TRUE, _("True")), (FALSE, _("False")))}), #TODO: factorise
        _IsEmptyOperator:          (DynamicSelect,
                                    {'auto': False},
                                    {'options': ((TRUE, _("True")), (FALSE, _("False")))}),
    }

#Form Widgets-------------------------------------------------------------------

boolean_str = lambda val: TRUE if val else FALSE


# class RegularFieldsConditionsWidget(SelectorList):
#     def __init__(self, fields, attrs=None):
#         chained_input = ChainedInput(attrs)
#         attrs = {'auto': False}
# 
#         chained_input.add_dselect('name',     options=self._build_fieldchoices(fields), attrs=attrs)
#         chained_input.add_dselect('operator', options=EntityFilterCondition._OPERATOR_MAP.iteritems(), attrs=attrs)
# 
#         pinput = PolymorphicInput(key='${operator}', attrs=attrs)
#         pinput.set_default_input(widget=DynamicInput, attrs=attrs)
# 
#         for optype, operator in EntityFilterCondition._OPERATOR_MAP.iteritems():
#             op_input = _CONDITION_INPUT_TYPE_MAP.get(type(operator))
# 
#             if op_input:
#                 input_widget, input_attrs, input_kwargs = op_input
#                 pinput.add_input(str(optype), widget=input_widget, attrs=input_attrs, **input_kwargs)
# 
#         chained_input.add_input('value', pinput, attrs=attrs)
# 
#         super(RegularFieldsConditionsWidget, self).__init__(chained_input)
# 
#     def _build_fieldchoices(self, fields):
#         fields_by_cat = defaultdict(list) #fields grouped by category (a category by FK)
# 
#         for fname, fieldlist in fields.iteritems():
#             if len(fieldlist) == 1:  #not a FK
#                 cat = ''
#                 vname = fieldlist[0].verbose_name
#             else: #FK case
#                 cat = unicode(fieldlist[0].verbose_name)
#                 vname = u'[%s] - %s' % (cat, fieldlist[1].verbose_name)
# 
#             fields_by_cat[cat].append((fname, vname))
# 
#         return [(cat, sorted(fields_by_cat[cat], key=lambda item: item[1]))
#                     for cat in sorted(fields_by_cat.keys())
#                ]


class FieldConditionWidget(ChainedInput):
    def __init__(self, fields, operators, attrs=None, autocomplete=False):
        super(FieldConditionWidget, self).__init__(attrs)
        field_attrs = {'auto': False, 'datatype': 'json'}

        if autocomplete:
            field_attrs['autocomplete'] = True

        operator_attrs = dict(field_attrs,
                              filter='context.field && item.value ? item.value.types.indexOf(context.field.type) !== -1 : true',
                              dependencies='field',
                             )
        self.add_dselect('field',    options=self._build_fieldchoices(fields), attrs=field_attrs)
        self.add_dselect('operator', options=self._build_operatorchoices(operators), attrs=operator_attrs)
        self.add_input('value', self._build_valueinput(field_attrs), attrs=attrs)

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(key='${field.type}.${operator.id}', attrs={'auto': False})
        pinput.add_dselect('^enum.*',
                           '/creme_core/enumerable/${field.ctype}/json', attrs=field_attrs)

        pinput.add_dselect('^user.(%d|%d)$' % (EntityFilterCondition.EQUALS, EntityFilterCondition.EQUALS_NOT),
                           '/creme_core/enumerable/userfilter/json', attrs=field_attrs,
                          )
        pinput.add_input('fk.(%d|%d)$' % (EntityFilterCondition.EQUALS, EntityFilterCondition.EQUALS_NOT),
                         EntitySelector, content_type='${field.ctype}', attrs={'auto': False},
                        )
        pinput.add_input('^date.%d$' % EntityFilterCondition.RANGE,
                         DateRangeSelect, attrs={'auto': False},
                        )
        pinput.add_input('^boolean.*',
                         DynamicSelect, options=((TRUE, _("True")), (FALSE, _("False"))), attrs=field_attrs,
                        )
        pinput.add_input('.(%d)$' % EntityFilterCondition.ISEMPTY,
                         DynamicSelect, options=((TRUE, _("True")), (FALSE, _("False"))), attrs=field_attrs,
                        )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    def _build_operatorchoices(self, operators):
        return [(json.dumps({'id': id, 'types': ' '.join(op.allowed_fieldtypes)}), op.name)
                    for id, op in operators.iteritems()
               ]

    def _build_fieldchoice(self, name, data):
        field = data[0]
        subfield = data[1] if len(data) > 1 else None
        category = ''

        if subfield is not None:
            category = field.verbose_name 
            choice_label = u'[%s] - %s' % (category, subfield.verbose_name)
            choice_value = {'name': name, 'type': FieldConditionWidget.field_choicetype(subfield)}
        else:
            choice_label = field.verbose_name
            choice_value = {'name': name, 'type': FieldConditionWidget.field_choicetype(field)}

        if choice_value['type'] in ('enum', 'fk'):
            choice_value['ctype'] = ContentType.objects.get_for_model(field.rel.to).id

        return category, (json.dumps(choice_value), choice_label)

    def _build_fieldchoices(self, fields):
        categories = defaultdict(list) #fields grouped by category (a category by FK)

        for fieldname, fieldlist in fields.iteritems():
            category, choice = self._build_fieldchoice(fieldname, fieldlist)
            categories[category].append(choice)

        # use collation sort
        return [(cat, sorted(categories[cat], key=lambda item: collator.sort_key(item[1])))
                    for cat in sorted(categories.keys(), key=collator.sort_key)
               ]

    @staticmethod
    def field_choicetype(field):
        if isinstance(field, ModelForeignKey):
            if issubclass(field.rel.to, User):
                return 'user'

            if issubclass(field.rel.to, CremeEntity):
                return 'fk'

            return 'enum'

        if isinstance(field, ModelDateField):
            return 'date'

        if isinstance(field, (ModelIntegerField, ModelFloatField, ModelDecimalField)):
            return 'number'

        if isinstance(field, ModelBooleanField):
            return 'boolean'

        return 'string'


#class DateFieldsConditionsWidget(SelectorList):
#    def __init__(self, date_fields_options, attrs=None, enabled=True):
#        chained_input = ChainedInput(attrs)
#        attrs = {'auto': False}
#
#        chained_input.add_dselect('field', options=date_fields_options, attrs=attrs)
#        chained_input.add_input('range', DateRangeSelect, attrs=attrs)
#
#        super(DateFieldsConditionsWidget, self).__init__(chained_input, enabled=enabled)
class DateFieldsConditionsWidget(SelectorList):
    def __init__(self, fields, attrs=None, enabled=True):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('field', options=self._build_fieldchoices(fields), attrs=attrs)
        chained_input.add_input('range', DateRangeSelect, attrs=attrs)

        super(DateFieldsConditionsWidget, self).__init__(chained_input, enabled=enabled)

    def _build_fieldchoice(self, name, data):
        field = data[0]
        subfield = data[1] if len(data) > 1 else None

        if subfield is not None:
            category = field.verbose_name
            choice_label = u'[%s] - %s' % (category, subfield.verbose_name) #TODO: factorise
        else:
            category = ''
            choice_label = field.verbose_name

        return category, (name, choice_label)

    #TODO: factorise (see FieldConditionWidget)
    def _build_fieldchoices(self, fields):
        categories = defaultdict(list) #fields grouped by category (a category by FK)

        for fieldname, fieldlist in fields.iteritems():
            category, choice = self._build_fieldchoice(fieldname, fieldlist)
            categories[category].append(choice)

        # use collation sort
        return [(cat, sorted(categories[cat], key=lambda item: collator.sort_key(item[1])))
                    for cat in sorted(categories.keys(), key=collator.sort_key)
               ]

# class CustomFieldsConditionsWidget(SelectorList): #todo: factorise with RegularFieldsConditionsWidget ???
#     def __init__(self, cfields, attrs=None, enabled=True):
#         chained_input = ChainedInput(attrs)
#         attrs = {'auto': False}
# 
#         chained_input.add_dselect('field',    options=cfields.iteritems(), attrs=attrs)
#         chained_input.add_dselect('operator', options=EntityFilterCondition._OPERATOR_MAP.iteritems(), attrs=attrs)
#         chained_input.add_input('value', DynamicInput, attrs=attrs)
# 
#         super(CustomFieldsConditionsWidget, self).__init__(chained_input, enabled=enabled)
class CustomFieldConditionWidget(FieldConditionWidget):
    def _build_fieldchoice(self, name, customfield):
        choice_label = customfield.name
        choice_value = {'id':   customfield.id,
                        'type': CustomFieldConditionWidget.customfield_choicetype(customfield),
                       }

        return '', (json.dumps(choice_value), choice_label)

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(key='${field.type}.${operator.id}', attrs={'auto': False})
        pinput.add_dselect('^enum.*',
                           '/creme_core/enumerable/custom/${field.id}/json', attrs=field_attrs,
                          )
        pinput.add_input('^date.%d$' % EntityFilterCondition.RANGE,
                         DateRangeSelect, attrs={'auto': False},
                        )
        pinput.add_input('^boolean.*',
                         DynamicSelect, options=((TRUE, _("True")), (FALSE, _("False"))), attrs=field_attrs,
                        )
        pinput.add_input('.(%d)$' % EntityFilterCondition.ISEMPTY,
                         DynamicSelect, options=((TRUE, _("True")), (FALSE, _("False"))), attrs=field_attrs,
                        )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    @staticmethod
    def customfield_choicetype(field): #TODO: use a dict...
        type = field.field_type

        if type in (CustomField.INT, CustomField.FLOAT):
            return 'number'

        if type == CustomField.BOOL:
            return 'boolean'

        if type == CustomField.DATETIME:
            return 'date'

        if type in (CustomField.ENUM, CustomField.MULTI_ENUM):
            return 'enum'

        return 'string'

    @staticmethod
    def customfield_rname_choicetype(value):
        type = value[len('customfield'):]

        if type in ('integer', 'double', 'float'):
            return 'number'

        return type


class DateCustomFieldsConditionsWidget(SelectorList):
    def __init__(self, date_fields_options, attrs=None, enabled=True):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        chained_input.add_dselect('field', options=date_fields_options, attrs=attrs)
        chained_input.add_input('range', DateRangeSelect, attrs=attrs)

        super(DateCustomFieldsConditionsWidget, self).__init__(chained_input, enabled=enabled)


class RelationTargetWidget(PolymorphicInput):
    def __init__(self, key='', multiple=False, attrs=None, **kwargs):
        super(RelationTargetWidget, self).__init__(key=key, attrs=attrs, **kwargs)
        self.add_input('^0$', widget=DynamicInput, type='hidden', attrs={'auto': False, 'value':'[]'})
        self.set_default_input(widget=EntitySelector, attrs={'auto': False, 'multiple': multiple})


class RelationsConditionsWidget(SelectorList):
    def __init__(self, rtypes, attrs=None):
        chained_input = ChainedInput(attrs)
        #datatype = json => boolean are retuned as json boolean, not strings
        attrs_json = {'auto': False, 'datatype': 'json'}

        rtype_name = 'rtype'
        ctype_url  = '/creme_core/entity_filter/rtype/${%s}/content_types' % rtype_name

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.iteritems(), attrs=attrs_json)
        add_dselect(rtype_name, options=rtypes, attrs={'auto': False, 'autocomplete': True})
        add_dselect("ctype", options=ctype_url, attrs=dict(attrs_json, autocomplete=True))

        chained_input.add_input("entity", widget=RelationTargetWidget, attrs={'auto': False}, key='${ctype}', multiple=True)

        super(RelationsConditionsWidget, self).__init__(chained_input)


class RelationSubfiltersConditionsWidget(SelectorList):
    def __init__(self, rtypes, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False, 'autocomplete': True}
        attrs_json = {'auto': False, 'datatype': 'json'}

        rtype_name = 'rtype'
        ctype_name = 'ctype'
        ctype_url  = '/creme_core/relation/type/${%s}/content_types/json' % rtype_name
        filter_url = '/creme_core/entity_filter/get_for_ctype/${%s}' % ctype_name

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.iteritems(), attrs=attrs_json)
        add_dselect(rtype_name, options=rtypes, attrs=attrs)
        add_dselect(ctype_name, options=ctype_url, attrs=dict(attrs_json, autocomplete=True))
        add_dselect("filter", options=filter_url, attrs={'auto': False, 'autocomplete': True, 'data-placeholder': _('Select')})

        super(RelationSubfiltersConditionsWidget, self).__init__(chained_input)


class PropertiesConditionsWidget(SelectorList):
    def __init__(self, ptypes, attrs=None):
        chained_input = ChainedInput(attrs)
        attrs = {'auto': False}

        add_dselect = chained_input.add_dselect #TODO: functools.partial
        add_dselect('has', options=_HAS_PROPERTY_OPTIONS.iteritems(), attrs={'auto': False, 'datatype': 'json'})
        add_dselect('ptype', options=ptypes, attrs=attrs)

        super(PropertiesConditionsWidget, self).__init__(chained_input)


#Form Fields--------------------------------------------------------------------

class _ConditionsField(JSONField):
    value_type = list

    def __init__(self, model=None, *args, **kwargs):
        super(_ConditionsField, self).__init__(*args, **kwargs)
        self.model = model or CremeEntity

    def initialize(self, ctype, conditions=None, efilter=None):
        self.model = ctype.model_class()

        if conditions:
            self._set_initial_conditions(conditions)

    @property
    def model(self):
        return self._model


class RegularFieldsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidfield':    _(u"This field is invalid with this model."),
        'invalidoperator': _(u"This operator is invalid."),
        'invalidvalue': _(u"This value is invalid.")
    }

    def _build_related_fields(self, field, fields):
        fname = field.name
        related_model = field.rel.to #TODO: inline

        if field.get_tag('enumerable'): #and not issubclass(related_model, CremeEntity):
            fields[field.name] = [field]

        for subfield in related_model._meta.fields:
            if subfield.get_tag('viewable') and not is_date_field(subfield):
                fields['%s__%s' % (fname, subfield.name)] =  [field, subfield]

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self._fields = fields = {}

        #TODO: use meta.ModelFieldEnumerator (need to be improved for grouped options)
        for field in model._meta.fields:
            if field.get_tag('viewable') and not is_date_field(field):
                if field.get_internal_type() == 'ForeignKey': #TODO: if isinstance(field, ModelForeignKey)
                    self._build_related_fields(field, fields)
                else:
                    fields[field.name] = [field]

        for field in model._meta.many_to_many:
            self._build_related_fields(field, fields)

        self._build_widget()

    def _create_widget(self):
        return SelectorList(FieldConditionWidget(self._fields, EntityFilterCondition._OPERATOR_MAP, autocomplete=True))

    def _value_to_jsonifiable(self, value):
        dicts = []

        field_choicetype = FieldConditionWidget.field_choicetype

        for condition in value:
            search_info = condition.decoded_value
            operator_id = search_info['operator']
            operator = EntityFilterCondition._OPERATOR_MAP.get(operator_id)

            #TODO: use polymorphism instead ??
            if isinstance(operator, _ConditionBooleanOperator):
                values = search_info['values'][0]
            else:
                values = u','.join(search_info['values'])

            field = self._fields[condition.name][-1]
            field_entry = {'name': condition.name, 'type': field_choicetype(field)}

            if field_entry['type'] in ('enum', 'fk'):
                field_entry['ctype'] = ContentType.objects.get_for_model(field.rel.to).id

            dicts.append({'field':    field_entry,
                          'operator': {'id': operator_id, 'types': ' '.join(operator.allowed_fieldtypes)},
                          'value':    values,
                         })

        return dicts

    def _clean_fieldname(self, entry):
        clean_value =  self.clean_value
        fname = clean_value(clean_value(entry, 'field', dict, required_error_key='invalidfield'),
                            'name', str, required_error_key='invalidfield')

        if fname not in self._fields:
            raise ValidationError(self.error_messages['invalidfield'])

        return fname

    def _clean_operator_n_values(self, entry):
        clean_value =  self.clean_value
        operator = clean_value(clean_value(entry, 'operator', dict, required_error_key='invalidoperator'),
                               'id', int, required_error_key='invalidoperator')

        operator_class = EntityFilterCondition._OPERATOR_MAP.get(operator)

        if not operator_class:
            raise ValidationError(self.error_messages['invalidoperator'])

        if isinstance(operator_class, _ConditionBooleanOperator):
            values = [clean_value(entry, 'value', bool, required_error_key='invalidvalue')]
        else:
            values = [v for v in clean_value(entry, 'value', unicode, required_error_key='invalidvalue').split(',') if v]

        return operator, values

    def _value_from_unjsonfied(self, data):
        build_4_field = EntityFilterCondition.build_4_field
        clean_fieldname = self._clean_fieldname
        clean_operator_n_values = self._clean_operator_n_values
        conditions = []

        try:
            for entry in data:
                operator, values = clean_operator_n_values(entry)
                conditions.append(build_4_field(model=self.model, name=clean_fieldname(entry),
                                                operator=operator, values=values
                                               )
                                 )
        except EntityFilterCondition.ValueError as e:
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

    def _build_related_fields(self, field, fields): #TODO: factorise with RegularFieldsConditionsField
        fname = field.name

        for subfield in field.rel.to._meta.fields:
            if subfield.get_tag('viewable') and is_date_field(subfield):
                fields['%s__%s' % (fname, subfield.name)] =  [field, subfield]

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        #self._fields = dict((field.name, field) for field in model._meta.fields if is_date_field(field))
        self._fields = fields = {}

        #TODO: factorise with RegularFieldsConditionsField
        #TODO: use meta.ModelFieldEnumerator (need to be improved for grouped options)
        for field in model._meta.fields:
            if field.get_tag('viewable'):
                if isinstance(field, ModelForeignKey):
                    self._build_related_fields(field, fields)
                elif is_date_field(field):
                    fields[field.name] = [field]

        for field in model._meta.many_to_many:
            self._build_related_fields(field, fields) #TODO: test

        self._build_widget()

    def _create_widget(self):
        #return DateFieldsConditionsWidget([(fname, f.verbose_name) for fname, f in self._fields.iteritems()],
                                          #enabled=len(self._fields) > 0
                                         #)
        return DateFieldsConditionsWidget(self._fields,
                                          #enabled=len(self._fields) > 0 TODO ?
                                         )

    def _format_date(self, date_dict):
        """@param date_dict dict or None; if not None => {"year": 2011, "month": 7, "day": 25}"""
        return date_format(date(**date_dict), 'DATE_FORMAT') if date_dict else ''

    def _value_to_jsonifiable(self, value):
        dicts = []
        format = self._format_date

        for condition in value:
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

    def _value_from_unjsonfied(self, data):
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
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        DATE = EntityFilterCondition.EFC_DATEFIELD
        self.initial = [c for c in conditions if c.type == DATE]


class CustomFieldsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidcustomfield': _(u"This custom field is invalid with this model."),
        'invalidoperator': _(u"This operator is invalid."),
        'invalidvalue': _(u"This value is invalid.")
    }

    _NOT_ACCEPTED_TYPES = frozenset((CustomField.DATETIME,)) #TODO: "!= DATE" instead

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self._cfields = cfields = \
            dict((cf.id, cf)
                    for cf in CustomField.objects
                                         .filter(content_type=ContentType.objects.get_for_model(model))
                                         .exclude(field_type__in=self._NOT_ACCEPTED_TYPES)
                )

        if not cfields:
            self._initial_help_text = self.help_text
            self.help_text = _('No custom field at present.')
            self.initial = ''
        else:
            self.help_text = getattr(self, '_initial_help_text', '')

        self._build_widget()

    def _create_widget(self):
        if not self._cfields:
            return Label()

        return SelectorList(CustomFieldConditionWidget(self._cfields, EntityFilterCondition._OPERATOR_MAP, autocomplete=True))

    def _value_to_jsonifiable(self, value):
        dicts = []

        customfield_rname_choicetype = CustomFieldConditionWidget.customfield_rname_choicetype

        for condition in value:
            search_info = condition.decoded_value
            operator_id = search_info['operator']
            operator = EntityFilterCondition._OPERATOR_MAP.get(operator_id)

            field_entry = {'id': int(condition.name), 'type': customfield_rname_choicetype(search_info['rname'])}

            dicts.append({'field':    field_entry,
                          'operator': {'id': operator_id, 'types': ' '.join(operator.allowed_fieldtypes)},
                          'value':    search_info['value'],
                         })

        return dicts

    def _clean_custom_field(self, entry):
        clean_value =  self.clean_value
        cfield_id = clean_value(clean_value(entry, 'field', dict, required_error_key='invalidcustomfield'), 
                                'id', int, required_error_key='invalidcustomfield')
        cfield = self._cfields.get(cfield_id)

        if not cfield:
            raise ValidationError(self.error_messages['invalidcustomfield'])

        return cfield

    def _clean_operator_n_values(self, entry):
        clean_value =  self.clean_value
        operator = clean_value(clean_value(entry, 'operator', dict, required_error_key='invalidoperator'), 
                               'id', int, required_error_key='invalidoperator')

        operator_class = EntityFilterCondition._OPERATOR_MAP.get(operator)

        if not operator_class:
            raise ValidationError(self.error_messages['invalidoperator'])

        if isinstance(operator_class, _ConditionBooleanOperator):
            values = [clean_value(entry, 'value', bool, required_error_key='invalidvalue')]
        else:
            values = clean_value(entry, 'value', unicode, required_error_key='invalidvalue').split(',')

        return operator, values

    def _value_from_unjsonfied(self, data):
        build_condition = EntityFilterCondition.build_4_customfield
        clean_cfield = self._clean_custom_field
        clean_operator_n_values = self._clean_operator_n_values
        conditions = []

        try:
            for entry in data:
                operator, values = clean_operator_n_values(entry)
                conditions.append(build_condition(custom_field=clean_cfield(entry),
                                                  operator=operator,
                                                  value=values[0]
                                                 )
                                 )
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        CUSTOMFIELD = EntityFilterCondition.EFC_CUSTOMFIELD
        filtered_conds = [c for c in conditions if c.type == CUSTOMFIELD]
        if filtered_conds:
            self.initial = filtered_conds


class DateCustomFieldsConditionsField(CustomFieldsConditionsField, DateFieldsConditionsField):
    default_error_messages = {
        'invalidcustomfield': _(u"This date custom field is invalid with this model."),
    }

    @CustomFieldsConditionsField.model.setter
    def model(self, model): #TODO: factorise ??
        self._model = model
        self._cfields = cfields = \
            dict((cf.id, cf)
                    for cf in CustomField.objects
                                         .filter(content_type=ContentType.objects.get_for_model(model),
                                                 field_type=CustomField.DATETIME,
                                                )
                )

        if not cfields:
            self._initial_help_text = self.help_text
            self.help_text = _('No date custom field at present.')
            self.initial = ''
        else:
            self.help_text = getattr(self, '_initial_help_text', '')

        self._build_widget()

    def _create_widget(self):
        if not self._cfields:
            return Label()

        #return DateFieldsConditionsWidget(self._cfields.iteritems())
        return DateCustomFieldsConditionsWidget(self._cfields.iteritems())

    def _value_to_jsonifiable(self, value):
        return DateFieldsConditionsField._value_to_jsonifiable(self, value)

    def _clean_custom_field(self, entry):
        cfield_id = self.clean_value(entry, 'field', int)
        cfield = self._cfields.get(cfield_id)

        if not cfield:
            raise ValidationError(self.error_messages['invalidcustomfield'])

        return cfield

    def _value_from_unjsonfied(self, data):
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
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        DATECUSTOMFIELD = EntityFilterCondition.EFC_DATECUSTOMFIELD
        filtered_conds = [c for c in conditions if c.type == DATECUSTOMFIELD]
        if filtered_conds:
            self.initial = filtered_conds


class RelationsConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidrtype':  _(u"This type of relationship type is invalid with this model."),
        'invalidct':     _(u"This content type is invalid."),
        'invalidentity': _(u"This entity is invalid."),
    }

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self._rtypes = dict((rt.id, rt) for rt in RelationType.get_compatible_ones(ContentType.objects.get_for_model(model), include_internals=True))
        self._build_widget()

    def _create_widget(self):
        return RelationsConditionsWidget(self._rtypes.iteritems())

    def _condition_to_dict(self, condition):
        value = condition.decoded_value
        ctype_id = 0

        #TODO: regroup queries....
        entity_id = value.get('entity_id')
        #if entity_id and not CremeEntity.objects.filter(pk=entity_id).exists():
        if entity_id:
            try:
                entity = CremeEntity.objects.get(pk=entity_id)
            except CremeEntity.DoesNotExist:
                entity_id = None
            else:
                ctype_id = entity.entity_type_id

        return {'rtype':  condition.name,
                'has':    boolean_str(value['has']),
                #'ctype':  value.get('ct_id', 0),
                'ctype':  ctype_id,
                'entity': entity_id,
               }

    #TODO: test with deleted entity ??
    def _value_to_jsonifiable(self, value):
        return list(map(self._condition_to_dict, value))

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

    def _value_from_unjsonfied(self, data):
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
                entity_id = kwargs.get('entity')
                if entity_id:
                    kwargs['entity'] = entities.get(entity_id)

        build_condition = EntityFilterCondition.build_4_relation

        try:
            conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except EntityFilterCondition.ValueError as e:
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
        filter_id = value['filter_id']

        return {'rtype':  condition.name,
                'has':    boolean_str(value['has']),
                 #TODO: regroup queries ? record in the condition to avoid the query,
                'ctype':  EntityFilter.objects.get(pk=filter_id).entity_type_id,
                'filter': filter_id,
               }

    def _value_from_unjsonfied(self, data):
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
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e))

        return conditions

    def _set_initial_conditions(self, conditions):
        RELATION_SUBFILTER = EntityFilterCondition.EFC_RELATION_SUBFILTER
        self.initial = [c for c in conditions if c.type == RELATION_SUBFILTER]


class PropertiesConditionsField(_ConditionsField):
    default_error_messages = {
        'invalidptype': _(u"This property type is invalid with this model."),
    }

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self._ptypes = dict((pt.id, pt) for pt in CremePropertyType.get_compatible_ones(ContentType.objects.get_for_model(model)))
        self._build_widget()

    def _create_widget(self):
        return PropertiesConditionsWidget(self._ptypes.iteritems())

    def _value_to_jsonifiable(self, value):
        return [{'ptype': condition.name,
                 'has':   boolean_str(condition.decoded_value),
                } for condition in value
               ]

    def _clean_ptype(self, entry):
        ptype = self._ptypes.get(self.clean_value(entry, 'ptype', str))

        if not ptype:
            raise ValidationError(self.error_messages['invalidptype'])

        return ptype

    def _value_from_unjsonfied(self, data):
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
    # Notice that we do not use 0/1 because it is linked to a boolean field,
    # so the value given to the widget for the selected choice is 'True' or 'False'...
    use_or = ChoiceField(label=_(u'The entity is accepted if'),
                         choices=(('False', _('all the conditions are met')),
                                  ('True',  _('any condition is met')),
                                 ),
                         widget=CremeRadioSelect,
                        )

    fields_conditions           = RegularFieldsConditionsField(label=_(u'On regular fields'), required=False,
                                                               help_text=_(u'You can write several values, separated by commas.')
                                                              )
    datefields_conditions       = DateFieldsConditionsField(label=_(u'On date fields'), required=False)
    customfields_conditions     = CustomFieldsConditionsField(label=_(u'On custom fields'), required=False,
                                                              #help_text=_(u'(Only integers, strings and decimals for now)')
                                                             )
    datecustomfields_conditions = DateCustomFieldsConditionsField(label=_(u'On date custom fields'), required=False)
    relations_conditions        = RelationsConditionsField(label=_(u'On relationships'), required=False,
                                                           help_text=_(u'Do not select any entity if you want to match them all.')
                                                          )
    relsubfilfers_conditions    = RelationSubfiltersConditionsField(label=_(u'On relationships with results of other filters'), required=False)
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
        user_field = self.fields['user']
        user_field.empty_label = _(u'All users')
        user_field.help_text   = _(u'All users can see this filter, but only the owner can edit or delete it')

    def get_cleaned_conditions(self):
        cdata = self.cleaned_data
        conditions = []

        for fname in self._CONDITIONS_FIELD_NAMES:
            conditions.extend(cdata[fname])

        return conditions

    def clean(self):
        cdata = super(_EntityFilterForm, self).clean()

        if not self._errors and not any(cdata[f] for f in self._CONDITIONS_FIELD_NAMES):
            raise ValidationError(ugettext(u'The filter must have at least one condition.'))

        return cdata


class EntityFilterCreateForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super(EntityFilterCreateForm, self).__init__(*args, **kwargs)
        self._entity_type = self.instance.entity_type = ct = self.initial['content_type']
        fields = self.fields

        for field_name in self._CONDITIONS_FIELD_NAMES:
            fields[field_name].initialize(ct)

        fields['use_or'].initial = 'False'

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        instance.is_custom = True
        #instance.entity_type = ct

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
            except EntityFilter.CycleError as e:
                raise ValidationError(e)

            cdata['all_conditions'] = conditions

        return cdata

    def save(self, *args, **kwargs):
        instance = super(EntityFilterEditForm, self).save(*args, **kwargs)
        instance.set_conditions(self.cleaned_data['all_conditions'], check_cycles=False)

        return instance
