# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from collections import defaultdict, OrderedDict
from datetime import date
import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import (ForeignKey as ModelForeignKey, DateField as ModelDateField,
        IntegerField as ModelIntegerField, FloatField as ModelFloatField,
        DecimalField as ModelDecimalField, BooleanField as ModelBooleanField,
        FileField as ModelFileField)
from django.db.models.fields.related import RelatedField as ModelRelatedField
from django.forms import ModelMultipleChoiceField, DateField, ChoiceField, ValidationError
from django.forms.fields import CallableChoiceIterator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.formats import date_format

from ..models import (CremeEntity, EntityFilter, EntityFilterCondition,
        RelationType, CremePropertyType, CustomField, CustomFieldBoolean, FieldsConfig)
from ..models.entity_filter import _ConditionBooleanOperator
from ..utils.date_range import date_range_registry
from ..utils.id_generator import generate_string_id_and_save
from ..utils.meta import is_date_field
from ..utils.unicode_collation import collator
from ..utils.url import TemplateURLBuilder
from .base import CremeModelForm
from .fields import JSONField
from .widgets import (DynamicInput, SelectorList, ChainedInput, Label,
        EntitySelector, DateRangeSelect,
        DynamicSelect, DynamicSelectMultiple, PolymorphicInput, CremeRadioSelect,
        NullableDateRangeSelect)


TRUE = 'true'
FALSE = 'false'

_BOOL_OPTIONS = ((TRUE, _('True')), (FALSE, _('False')))
_HAS_PROPERTY_OPTIONS = OrderedDict([
        (TRUE,  _('Has the property')),
        (FALSE, _('Does not have the property')),
    ])

_HAS_RELATION_OPTIONS = OrderedDict([
        (TRUE,  _('Has the relationship')),
        (FALSE, _('Does not have the relationship')),
    ])


# Form Widgets------------------------------------------------------------------

boolean_str = lambda val: TRUE if val else FALSE


class FieldConditionWidget(ChainedInput):  # TODO: rename FieldConditionSelector ??
    def __init__(self, model=CremeEntity, fields=(), operators=(), attrs=None, autocomplete=False):
        super().__init__(attrs)
        self.model = model
        self.fields = fields
        self.operators = operators
        self.autocomplete = autocomplete

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(key='${field.type}.${operator.id}', attrs={'auto': False})

        EQUALS_OPS = '{}|{}'.format(EntityFilterCondition.EQUALS, EntityFilterCondition.EQUALS_NOT)
        add_input = pinput.add_input
        add_input('^enum(__null)?.({})$'.format(EQUALS_OPS),
                  widget=DynamicSelectMultiple, attrs=field_attrs,
                  # TODO: use a GET arg instead of using a TemplateURLBuilder ?
                  # TODO: remove "field.ctype" ?
                  url=TemplateURLBuilder(field=(TemplateURLBuilder.Word, '${field.name}'))
                                        .resolve('creme_core__enumerable_choices',
                                                 kwargs={'ct_id': ContentType.objects.get_for_model(self.model).id},
                                                ),
                 )

        pinput.add_dselect('^user(__null)?.({})$'.format(EQUALS_OPS),
                           reverse('creme_core__efilter_user_choices'),
                           attrs=field_attrs,
                          )
        add_input('^fk(__null)?.({})$'.format(EQUALS_OPS),
                  widget=EntitySelector, attrs={'auto': False},
                  content_type='${field.ctype}',
                 )
        add_input('^date(__null)?.{}$'.format(EntityFilterCondition.RANGE),
                  widget=DateRangeSelect, attrs={'auto': False},
                 )
        add_input('^boolean(__null)?.*', widget=DynamicSelect,
                  options=_BOOL_OPTIONS, attrs=field_attrs,
                 )
        add_input('(string|.*__null).({})$'.format(EntityFilterCondition.ISEMPTY),
                  widget=DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
                 )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    def _build_operatorchoices(self, operators):
        return [(json.dumps({'id': id, 'types': ' '.join(op.allowed_fieldtypes)}), op.name)
                    for id, op in operators.items()
               ]

    def _build_fieldchoice(self, name, data):
        field = data[0]
        subfield = data[1] if len(data) > 1 else None
        category = ''

        if subfield is not None:
            category = field.verbose_name
            choice_type = self.field_choicetype(subfield)
            choice_label = '[{}] - {}'.format(category, subfield.verbose_name)
            choice_value = {'name': name, 'type': choice_type}

            if choice_type in EntityFilterCondition._FIELDTYPES_RELATED:
                choice_value['ctype'] = ContentType.objects.get_for_model(subfield.remote_field.model).id
        else:
            choice_type = self.field_choicetype(field)
            choice_label = field.verbose_name
            choice_value = {'name': name, 'type': choice_type}

            if choice_type in EntityFilterCondition._FIELDTYPES_RELATED:
                choice_value['ctype'] = ContentType.objects.get_for_model(field.remote_field.model).id

        return category, (json.dumps(choice_value), choice_label)

    def _build_fieldchoices(self, fields):
        categories = defaultdict(list)  # Fields grouped by category (a category by FK)

        for fieldname, fieldlist in fields:
            category, choice = self._build_fieldchoice(fieldname, fieldlist)
            categories[category].append(choice)

        sort_key = collator.sort_key

        return [(cat, sorted(categories[cat], key=lambda item: sort_key(item[1])))
                    for cat in sorted(categories.keys(), key=sort_key)
               ]

    @staticmethod
    def field_choicetype(field):
        isnull = '__null' if field.null or field.many_to_many else ''

        if isinstance(field, ModelRelatedField):
            if issubclass(field.remote_field.model, get_user_model()):
                return 'user' + isnull

            if not issubclass(field.remote_field.model, CremeEntity) and field.get_tag('enumerable'):
                return 'enum' + isnull

            return 'fk' + isnull

        if isinstance(field, ModelDateField):
            return 'date' + isnull

        if isinstance(field, (ModelIntegerField, ModelFloatField, ModelDecimalField)):
            return 'number' + isnull

        if isinstance(field, ModelBooleanField):
            return 'boolean' + isnull

        return 'string'

    def get_context(self, name, value, attrs):
        field_attrs = {'auto': False, 'datatype': 'json'}

        if self.autocomplete:
            field_attrs['autocomplete'] = True

        add_dselect = self.add_dselect
        add_dselect('field',    options=self._build_fieldchoices(self.fields), attrs=field_attrs)
        add_dselect('operator', options=self._build_operatorchoices(self.operators),
                    attrs={
                        **field_attrs,
                        'filter': 'context.field && item.value ? '
                                  'item.value.types.split(" ").indexOf(context.field.type) !== -1 : '
                                  'true',
                        'dependencies': 'field',
                    },
                   )
        self.add_input('value', self._build_valueinput(field_attrs), attrs=attrs)

        return super().get_context(name=name, value=value, attrs=attrs)


class RegularFieldsConditionsWidget(SelectorList):
    def __init__(self, model=CremeEntity, fields=(), attrs=None, enabled=True):  # TODO: use/remove 'enabled'
        super().__init__(None, attrs)
        self.model = model
        self.fields = fields

    def get_context(self, name, value, attrs):
        self.selector = FieldConditionWidget(model=self.model,
                                             fields=self.fields,
                                             # TODO: given by form field ?
                                             operators=EntityFilterCondition._OPERATOR_MAP,
                                             autocomplete=True,
                                            )

        return super().get_context(name=name, value=value, attrs=attrs)


class DateFieldsConditionsWidget(SelectorList):
    def __init__(self, fields=(), attrs=None, enabled=True):
        super().__init__(None, enabled=enabled, attrs=attrs)
        self.fields = fields

    def _build_fieldchoice(self, name, data):
        field = data[0]
        subfield = data[1] if len(data) > 1 else None

        if subfield is not None:
            category = field.verbose_name
            choice_label = '[{}] - {}'.format(category, subfield.verbose_name)  # TODO: factorise
            is_null = subfield.null
        else:
            category = ''
            choice_label = field.verbose_name
            is_null = field.null

        choice_value = {'name': name, 'type': 'daterange__null' if is_null else 'daterange'}
        return category, (json.dumps(choice_value), choice_label)

    # TODO: factorise (see FieldConditionWidget)
    def _build_fieldchoices(self, fields):
        categories = defaultdict(list)  # Fields grouped by category (a category by FK)

        for fieldname, fieldlist in fields:
            category, choice = self._build_fieldchoice(fieldname, fieldlist)
            categories[category].append(choice)

        return [(cat, sorted(categories[cat], key=lambda item: collator.sort_key(item[1])))
                    for cat in sorted(categories.keys(), key=collator.sort_key)
               ]

    def get_context(self, name, value, attrs):
        self.selector = chained_input = ChainedInput()
        sub_attrs = {'auto': False, 'datatype': 'json'}

        chained_input.add_dselect('field', options=self._build_fieldchoices(self.fields), attrs=sub_attrs)

        pinput = PolymorphicInput(key='${field.type}', attrs=sub_attrs)
        pinput.add_input('daterange__null', NullableDateRangeSelect, attrs=sub_attrs)
        pinput.add_input('daterange', DateRangeSelect, attrs=sub_attrs)

        chained_input.add_input('range', pinput, attrs=sub_attrs)

        return super().get_context(name=name, value=value, attrs=attrs)


class CustomFieldConditionSelector(FieldConditionWidget):
    _CHOICETYPES = {
        CustomField.INT:        'number__null',
        CustomField.FLOAT:      'number__null',
        CustomField.DATETIME:   'date__null',
        CustomField.BOOL:       'boolean__null',
        CustomField.ENUM:       'enum__null',
        CustomField.MULTI_ENUM: 'enum__null',
    }

    def _build_fieldchoice(self, name, customfield):
        choice_label = customfield.name
        choice_value = {'id':   customfield.id,
                        'type': CustomFieldConditionSelector.customfield_choicetype(customfield),
                       }

        return '', (json.dumps(choice_value), choice_label)

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(key='${field.type}.${operator.id}', attrs={'auto': False})
        pinput.add_input('^enum(__null)?.({}|{})$'.format(EntityFilterCondition.EQUALS,
                                                          EntityFilterCondition.EQUALS_NOT,
                                                         ),
                         widget=DynamicSelectMultiple,
                         # TODO: use a GET arg instead of using a TemplateURLBuilder ?
                         url=TemplateURLBuilder(cf_id=(TemplateURLBuilder.Int, '${field.id}'))
                                               .resolve('creme_core__cfield_enums'),
                         attrs=field_attrs,
                        )
        pinput.add_input('^date(__null)?.{}$'.format(EntityFilterCondition.RANGE),
                         NullableDateRangeSelect, attrs={'auto': False},
                        )
        pinput.add_input('^boolean(__null)?.*',
                         DynamicSelect, options=((TRUE, _('True')), (FALSE, _('False'))), attrs=field_attrs,
                        )
        pinput.add_input('(string|.*__null)?.({})$'.format(EntityFilterCondition.ISEMPTY),
                         DynamicSelect, options=((TRUE, _('True')), (FALSE, _('False'))), attrs=field_attrs,
                        )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    @staticmethod
    def customfield_choicetype(field):
        return CustomFieldConditionSelector._CHOICETYPES.get(field.field_type, 'string')

    @staticmethod
    def customfield_rname_choicetype(value):
        type = value[len('customfield'):]

        if type == 'string':
            return 'string'

        if type in {'integer', 'double', 'float'}:
            return 'number__null'

        if type in {'enum', 'multienum'}:
            return 'enum__null'

        return type + '__null'


# TODO: factorise RegularFieldsConditionsWidget ?
class CustomFieldConditionWidget(SelectorList):
    template_name = 'creme_core/forms/widgets/efilter-cfield-conditions.html'

    def __init__(self, fields=(), attrs=None, enabled=True):
        super().__init__(None, attrs)
        self.fields = fields

    def get_context(self, name, value, attrs):
        fields = list(self.fields)

        if not fields:
            return Label(empty_label=_('No custom field at present.'))\
                        .get_context(name=name, value=value, attrs=attrs)

        self.selector = CustomFieldConditionSelector(fields=fields, autocomplete=True,
                                                     # TODO: given by form field ?
                                                     operators=EntityFilterCondition._OPERATOR_MAP,
                                                    )

        return super().get_context(name=name, value=value, attrs=attrs)


class DateCustomFieldsConditionsWidget(SelectorList):
    template_name = 'creme_core/forms/widgets/efilter-cfield-conditions.html'

    def __init__(self, date_fields_options=(), attrs=None, enabled=True):
        super().__init__(selector=None, enabled=enabled, attrs=attrs)
        self.date_fields_options = date_fields_options

    def get_context(self, name, value, attrs):
        options = list(self.date_fields_options)

        if not options:
            return Label(empty_label=_('No date custom field at present.'))\
                        .get_context(name=name, value=value, attrs=attrs)

        self.selector = chained_input = ChainedInput()
        sub_attrs = {'auto': False}

        chained_input.add_dselect('field', options=options, attrs=sub_attrs)
        chained_input.add_input('range', NullableDateRangeSelect, attrs=sub_attrs)

        return super().get_context(name=name, value=value, attrs=attrs)


class RelationTargetWidget(PolymorphicInput):
    def __init__(self, key='', multiple=False, attrs=None):
        super().__init__(key=key, attrs=attrs)
        self.add_input('^0$', widget=DynamicInput, type='hidden', attrs={'auto': False, 'value':'[]'})
        self.set_default_input(widget=EntitySelector, attrs={'auto': False, 'multiple': multiple})


class RelationsConditionsWidget(SelectorList):
    def __init__(self, rtypes=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.rtypes = rtypes

    def get_context(self, name, value, attrs):
        self.selector = chained_input = ChainedInput()
        # datatype = json => boolean are returned as json boolean, not strings
        attrs_json = {'auto': False, 'datatype': 'json'}

        rtype_name = 'rtype'
        # TODO: use a GET arg instead of using a TemplateURLBuilder ?
        ctype_url = TemplateURLBuilder(rtype_id=(TemplateURLBuilder.Word, '${%s}' % rtype_name))\
                                      .resolve('creme_core__ctypes_compatible_with_rtype_as_choices')

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.items(), attrs=attrs_json)
        add_dselect(rtype_name, options=self.rtypes, attrs={'auto': False, 'autocomplete': True})
        add_dselect('ctype', options=ctype_url, attrs={**attrs_json, 'autocomplete': True})

        chained_input.add_input('entity', widget=RelationTargetWidget,
                                attrs={'auto': False}, key='${ctype}', multiple=True,
                               )

        return super().get_context(name=name, value=value, attrs=name)


class RelationSubfiltersConditionsWidget(SelectorList):
    def __init__(self, rtypes=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.rtypes = rtypes

    def get_context(self, name, value, attrs):
        self.selector = chained_input = ChainedInput()

        attrs_json = {'auto': False, 'datatype': 'json'}
        rtype_name = 'rtype'
        ctype_name = 'ctype'

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.items(), attrs=attrs_json)
        add_dselect(rtype_name, options=self.rtypes, attrs={'auto': False, 'autocomplete': True})
        add_dselect(ctype_name, attrs={**attrs_json, 'autocomplete': True},
                    # TODO: use a GET arg instead of using a TemplateURLBuilder ?
                    options=TemplateURLBuilder(rtype_id=(TemplateURLBuilder.Word, '${%s}' % rtype_name))
                                              .resolve('creme_core__ctypes_compatible_with_rtype'),
                   )
        add_dselect('filter',
                    options=reverse('creme_core__efilters') + '?ct_id=${%s}' % ctype_name,
                    attrs={'auto': False, 'autocomplete': True, 'data-placeholder': _('(no filter)')},
                   )

        return super().get_context(name=name, value=value, attrs=attrs)


class PropertiesConditionsWidget(SelectorList):
    def __init__(self, ptypes=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.ptypes = ptypes

    def get_context(self, name, value, attrs):
        self.selector = chained_input = ChainedInput(attrs)

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_PROPERTY_OPTIONS.items(),
                    attrs={'auto': False, 'datatype': 'json'},
                   )
        add_dselect('ptype', options=self.ptypes, attrs={'auto': False})

        return super().get_context(name=name, value=value, attrs=attrs)


# Form Fields-------------------------------------------------------------------

class _ConditionsField(JSONField):
    value_type = list
    _model = None

    # def __init__(self, model=CremeEntity, *args, **kwargs):
    def __init__(self, *, model=CremeEntity, **kwargs):
        # super().__init__(*args, **kwargs)
        super().__init__(**kwargs)
        self.model = model

    def initialize(self, ctype, conditions=None, efilter=None):
        if conditions:
            self._set_initial_conditions(conditions)

        self.model = ctype.model_class()

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model


class RegularFieldsConditionsField(_ConditionsField):
    widget = RegularFieldsConditionsWidget
    default_error_messages = {
        'invalidfield':    _('This field is invalid with this model.'),
        'invalidoperator': _('This operator is invalid.'),
        'invalidvalue':    _('This value is invalid.'),
    }
    excluded_fields = (ModelFileField,)

    _non_hiddable_fnames = ()
    _fields = None

    def _build_related_fields(self, field, fields, fconfigs):
        fname = field.name
        related_model = field.remote_field.model
        field_hidden = fconfigs.get_4_model(field.model).is_field_hidden(field)
        excluded = self.excluded_fields
        non_hiddable_fnames = self._non_hiddable_fnames

        if field.get_tag('enumerable') and (not field_hidden or fname in non_hiddable_fnames):
            fields[field.name] = [field]

        is_sfield_hidden = fconfigs.get_4_model(related_model).is_field_hidden

        for subfield in related_model._meta.fields:
            if subfield.get_tag('viewable') and not is_date_field(subfield) \
               and not isinstance(subfield, excluded):
                full_name = '{}__{}'.format(fname, subfield.name)

                if not (field_hidden or is_sfield_hidden(subfield)) or \
                   full_name in non_hiddable_fnames:
                    fields[full_name] = [field, subfield]

    @_ConditionsField.model.setter
    def model(self, model):
        if self._model != model:
            self._model = model
            self._fields = None  # Clear cache

            widget = self.widget
            widget.model = model
            widget.fields = CallableChoiceIterator(lambda: self._get_fields().items())

    def _get_fields(self):
        if self._fields is None:
            self._fields = fields = {}
            model = self._model
            non_hiddable_fnames = self._non_hiddable_fnames
            fconfigs = FieldsConfig.LocalCache()
            is_field_hidden = fconfigs.get_4_model(model).is_field_hidden
            excluded = self.excluded_fields

            # TODO: use meta.ModelFieldEnumerator (need to be improved for grouped options)
            for field in model._meta.fields:
                if field.get_tag('viewable') and not is_date_field(field) \
                   and not isinstance(field, excluded):
                    if isinstance(field, ModelForeignKey):
                        self._build_related_fields(field, fields, fconfigs)
                    elif not is_field_hidden(field) or field.name in non_hiddable_fnames:
                        fields[field.name] = [field]

            for field in model._meta.many_to_many:
                if field.get_tag('viewable'):  # TODO: test not viewable
                    self._build_related_fields(field, fields, fconfigs)

        return self._fields

    def _value_to_jsonifiable(self, value):
        fields = self._get_fields()
        dicts = []
        field_choicetype = FieldConditionWidget.field_choicetype

        for condition in value:
            search_info = condition.decoded_value
            operator_id = search_info['operator']
            operator = EntityFilterCondition._OPERATOR_MAP.get(operator_id)

            field = fields[condition.name][-1]
            field_entry = {'name': condition.name, 'type': field_choicetype(field)}

            # TODO: use polymorphism instead ??
            if isinstance(operator, _ConditionBooleanOperator):
                values = search_info['values'][0]
            elif isinstance(field, ModelBooleanField):
                values = search_info['values'][0]
            else:
                values = ','.join(str(value) for value in search_info['values'])

            if field_entry['type'] in EntityFilterCondition._FIELDTYPES_RELATED:
                field_entry['ctype'] = ContentType.objects.get_for_model(field.remote_field.model).id

            dicts.append({'field':    field_entry,
                          'operator': {'id':    operator_id,
                                       'types': ' '.join(operator.allowed_fieldtypes),
                                      },
                          'value':    values,
                         })

        return dicts

    def _clean_fieldname(self, entry):
        clean_value = self.clean_value
        fname = clean_value(clean_value(entry, 'field', dict, required_error_key='invalidfield'),
                            'name', str, required_error_key='invalidfield')

        if fname not in self._fields:
            raise ValidationError(self.error_messages['invalidfield'], code='invalidfield')

        return fname

    def _clean_operator_n_values(self, entry):
        clean_value = self.clean_value
        operator = clean_value(clean_value(entry, 'operator', dict, required_error_key='invalidoperator'),
                               'id', int, required_error_key='invalidoperator')

        operator_class = EntityFilterCondition._OPERATOR_MAP.get(operator)

        if not operator_class:
            raise ValidationError(self.error_messages['invalidoperator'], code='invalidoperator')

        if isinstance(operator_class, _ConditionBooleanOperator):
            values = [clean_value(entry, 'value', bool, required_error_key='invalidvalue')]
        elif entry is None:
            values = self._return_none_or_raise(self.required, 'invalidvalue')
        elif isinstance(entry.get('value'), list):
            values = [v for v in clean_value(entry, 'value', list, required_error_key='invalidvalue') if v]
        elif isinstance(entry.get('value'), bool):
            values = [entry.get('value')]
        else:
            values = [v for v in clean_value(entry, 'value', str, required_error_key='invalidvalue').split(',') if v]

        return operator, values

    def _value_from_unjsonfied(self, data):
        build_4_field = EntityFilterCondition.build_4_field
        clean_fieldname = self._clean_fieldname
        clean_operator_n_values = self._clean_operator_n_values
        conditions = []
        self._get_fields()  # Build self._fields

        try:
            for entry in data:
                operator, values = clean_operator_n_values(entry)
                conditions.append(build_4_field(model=self.model, name=clean_fieldname(entry),
                                                operator=operator,
                                                values=values,
                                                user=self.user,
                                               )
                                 )
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        FIELD = EntityFilterCondition.EFC_FIELD
        self.initial = f_conds = [c for c in conditions if c.type == FIELD]
        self._non_hiddable_fnames = {c.name for c in f_conds}


class DateFieldsConditionsField(_ConditionsField):
    widget = DateFieldsConditionsWidget
    default_error_messages = {
        'invalidfield':     _('This field is not a date field for this model.'),
        'invaliddaterange': _('This date range is invalid.'),
        'emptydates':       _('Please enter a start date and/or a end date.'),
    }

    _non_hiddable_fnames = ()
    _fields = None

    # TODO: factorise with RegularFieldsConditionsField
    def _build_related_fields(self, field, fields, fconfigs):
        fname = field.name
        related_model = field.remote_field.model
        field_hidden = fconfigs.get_4_model(field.model).is_field_hidden(field)
        is_sfield_hidden = fconfigs.get_4_model(related_model).is_field_hidden
        non_hiddable_fnames = self._non_hiddable_fnames

        for subfield in related_model._meta.fields:
            if subfield.get_tag('viewable') and is_date_field(subfield):
                full_name = '{}__{}'.format(fname, subfield.name)

                if not (field_hidden or is_sfield_hidden(subfield)) or \
                   full_name in non_hiddable_fnames:
                    fields[full_name] = [field, subfield]

    # TODO: factorise with RegularFieldsConditionsField
    @_ConditionsField.model.setter
    def model(self, model):
        if self._model != model:
            self._model = model
            self._fields = None  # Clear cache

            self.widget.fields = CallableChoiceIterator(lambda: self._get_fields().items())

    def _get_fields(self):
        if self._fields is None:
            self._fields = fields = {}
            model = self.model
            non_hiddable_fnames = self._non_hiddable_fnames
            fconfigs = FieldsConfig.LocalCache()
            is_field_hidden = fconfigs.get_4_model(model).is_field_hidden

            # TODO: use meta.ModelFieldEnumerator (need to be improved for grouped options)
            for field in model._meta.fields:
                if field.get_tag('viewable'):
                    if isinstance(field, ModelForeignKey):
                        self._build_related_fields(field, fields, fconfigs)
                    elif is_date_field(field) and (not is_field_hidden(field) or
                         field.name in non_hiddable_fnames):
                        fields[field.name] = [field]

            for field in model._meta.many_to_many:
                self._build_related_fields(field, fields, fconfigs) # TODO: test

        return self._fields

    def _format_date(self, date_dict):
        """@param date_dict: dict or None; if not None => {"year": 2011, "month": 7, "day": 25}"""
        return date_format(date(**date_dict), 'DATE_FORMAT') if date_dict else ''

    # TODO: factorise with RegularFieldsConditionsField
    def _value_to_jsonifiable(self, value):
        fields = self._get_fields()
        dicts = []
        fmt = self._format_date

        for condition in value:
            get = condition.decoded_value.get
            field = fields[condition.name][-1]

            dicts.append({'field': {'name': condition.name,
                                    'type': 'daterange' if not field.null else 'daterange__null',
                                   },
                          'range': {'type':  get('name', ''),
                                    'start': fmt(get('start')),
                                    'end':   fmt(get('end'))
                                   },
                         })

        return dicts

    def _clean_date_range(self, entry):
        range_info = entry.get('range')

        if not isinstance(range_info, dict):
            raise ValidationError(self.error_messages['invalidformat'], code='invalidformat')

        range_type = range_info.get('type') or None
        start = None
        end   = None

        if not range_type:
            start_str = range_info.get('start')
            end_str   = range_info.get('end')

            if not start_str and not end_str:
                raise ValidationError(self.error_messages['emptydates'], code='emptydates')

            clean_date = DateField().clean

            if start_str:
                start = clean_date(start_str)

            if end_str:
                end = clean_date(end_str)
        elif not date_range_registry.get_range(name=range_type):
            raise ValidationError(self.error_messages['invaliddaterange'], code='invaliddaterange')

        return (range_type, start, end)

    def _clean_field_name(self, entry):
        clean_value = self.clean_value
        fname = clean_value(clean_value(entry, 'field', dict, required_error_key='invalidfield'),
                            'name', str, required_error_key='invalidfield',
                           )

        if not fname in self._get_fields():
            raise ValidationError(self.error_messages['invalidfield'], code='invalidfield')

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
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        DATE = EntityFilterCondition.EFC_DATEFIELD
        self.initial = f_conds = [c for c in conditions if c.type == DATE]
        self._non_hiddable_fnames = {c.name for c in f_conds}


class CustomFieldsConditionsField(_ConditionsField):
    widget = CustomFieldConditionWidget
    default_error_messages = {
        'invalidcustomfield': _('This custom field is invalid with this model.'),
        'invalidoperator':    _('This operator is invalid.'),
        'invalidvalue':       _('This value is invalid.'),
    }

    _NOT_ACCEPTED_TYPES = frozenset((CustomField.DATETIME,)) # TODO: "!= DATE" instead

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self.widget.fields = CallableChoiceIterator(lambda: [(cf.id, cf) for cf in self._get_cfields()])

    def _get_cfields(self):
        return CustomField.objects.filter(content_type=ContentType.objects.get_for_model(self._model)) \
                                  .exclude(field_type__in=self._NOT_ACCEPTED_TYPES)

    def _value_to_jsonifiable(self, value):
        dicts = []
        customfield_rname_choicetype = CustomFieldConditionSelector.customfield_rname_choicetype
        get_op = EntityFilterCondition._OPERATOR_MAP.get

        for condition in value:
            search_info = condition.decoded_value
            operator_id = search_info['operator']
            operator = get_op(operator_id)

            field_type = customfield_rname_choicetype(search_info['rname'])
            field_entry = {'id': int(condition.name), 'type': field_type}

            value = ','.join(str(v) for v in search_info['value'])

            # HACK : lower serialisation of boolean (combobox waiting for 'true' and not 'True')
            if search_info['rname'] == CustomFieldBoolean.get_related_name():
                value = value.lower()

            dicts.append({'field':    field_entry,
                          'operator': {'id': operator_id, 'types': ' '.join(operator.allowed_fieldtypes)},
                          'value':    value,
                         })

        return dicts

    def _clean_custom_field(self, entry):
        clean_value =  self.clean_value
        cfield_id = clean_value(clean_value(entry, 'field', dict,
                                            required_error_key='invalidcustomfield',
                                           ),
                                'id', int, required_error_key='invalidcustomfield',
                               )

        # TODO: regroup queries
        try:
            cfield = self._get_cfields().get(id=cfield_id)
        except CustomField.DoesNotExist as e:
            raise ValidationError(self.error_messages['invalidcustomfield'],
                                  code='invalidcustomfield',
                                 ) from e

        return cfield

    def _clean_operator_n_values(self, entry):
        clean_value =  self.clean_value
        operator = clean_value(clean_value(entry, 'operator', dict,
                                           required_error_key='invalidoperator',
                                          ),
                               'id', int, required_error_key='invalidoperator',
                              )

        operator_class = EntityFilterCondition._OPERATOR_MAP.get(operator)

        if not operator_class:
            raise ValidationError(self.error_messages['invalidoperator'],
                                  code='invalidoperator',
                                 )

        if isinstance(operator_class, _ConditionBooleanOperator):
            values = [clean_value(entry, 'value', bool, required_error_key='invalidvalue')]
        elif entry is None:
            values = self._return_none_or_raise(self.required, 'invalidvalue')
        elif isinstance(entry.get('value'), list):
            values = [v for v in clean_value(entry, 'value', list,
                                             required_error_key='invalidvalue',
                                            )
                            if v
                    ]
        elif isinstance(entry.get('value'), bool):
            values = [entry.get('value')]
        else:
            values = [v for v in clean_value(entry, 'value', str,
                                             required_error_key='invalidvalue',
                                            ).split(',')
                            if v
                     ]

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
                                                  value=values,
                                                  user=self.user,
                                                 )
                                 )
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        CUSTOMFIELD = EntityFilterCondition.EFC_CUSTOMFIELD
        filtered_conds = [c for c in conditions if c.type == CUSTOMFIELD]
        if filtered_conds:
            self.initial = filtered_conds


class DateCustomFieldsConditionsField(CustomFieldsConditionsField, DateFieldsConditionsField):
    widget = DateCustomFieldsConditionsWidget
    default_error_messages = {
        'invalidcustomfield': _('This date custom field is invalid with this model.'),
    }

    @CustomFieldsConditionsField.model.setter
    def model(self, model):  # TODO: factorise ??
        self._model = model
        self.widget.date_fields_options = CallableChoiceIterator(lambda: [(cf.id, cf) for cf in self._get_cfields()])

    def _get_cfields(self):
        return CustomField.objects.filter(content_type=ContentType.objects.get_for_model(self._model),
                                          field_type=CustomField.DATETIME,
                                         )

    def _value_to_jsonifiable(self, value):
        dicts = []
        fmt = self._format_date

        for condition in value:
            get = condition.decoded_value.get

            dicts.append({'field': int(condition.name),
                          'range': {'type':  get('name', ''),
                                    'start': fmt(get('start')),
                                    'end':   fmt(get('end'))
                                   },
                         })

        return dicts

    def _clean_custom_field(self, entry):
        cfield_id = self.clean_value(entry, 'field', int)

        # TODO: regroup queries
        try:
            cfield = self._get_cfields().get(id=cfield_id)
        except CustomField.DoesNotExist as e:
            raise ValidationError(self.error_messages['invalidcustomfield'],
                                  code='invalidcustomfield',
                                 ) from e

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
                                                  date_range=date_range, start=start, end=end,
                                                 )
                                 )
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        DATECUSTOMFIELD = EntityFilterCondition.EFC_DATECUSTOMFIELD
        filtered_conds = [c for c in conditions if c.type == DATECUSTOMFIELD]
        if filtered_conds:
            self.initial = filtered_conds


class RelationsConditionsField(_ConditionsField):
    widget = RelationsConditionsWidget
    default_error_messages = {
        'invalidrtype':  _('This type of relationship type is invalid with this model.'),
        'invalidct':     _('This content type is invalid.'),
        'invalidentity': _('This entity is invalid.'),
    }

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self.widget.rtypes = CallableChoiceIterator(lambda: [(rt.id, rt) for rt in self._get_rtypes()])

    def _get_rtypes(self):
        return RelationType.objects.compatible(self._model, include_internals=True)

    def _condition_to_dict(self, condition):
        value = condition.decoded_value
        ctype_id = 0

        # TODO: regroup queries....
        entity_id = value.get('entity_id')
        if entity_id:
            try:
                entity = CremeEntity.objects.get(pk=entity_id)
            except CremeEntity.DoesNotExist:
                entity_id = None
            else:
                ctype_id = entity.entity_type_id

        return {'rtype':  condition.name,
                'has':    boolean_str(value['has']),
                'ctype':  ctype_id,
                'entity': entity_id,
               }

    # TODO: test with deleted entity ??
    def _value_to_jsonifiable(self, value):
        return list(map(self._condition_to_dict, value))

    def _clean_ct(self, entry):
        ct_id = self.clean_value(entry, 'ctype', int)

        if ct_id:
            try:
                ct = ContentType.objects.get_for_id(ct_id)
            except ContentType.DoesNotExist as e:
                raise ValidationError(self.error_messages['invalidct'], code='invalidct') from e

            return ct

    def _clean_entity_id(self, entry):
        entity_id = entry.get('entity')  # TODO: improve clean_value with default value ???

        if entity_id:
            try:
                return int(entity_id)
            except ValueError as e:
                raise ValidationError(self.error_messages['invalidformat'], code='invalidformat') from e

    def _clean_rtype(self, entry):
        rtype_id = self.clean_value(entry, 'rtype', str)

        # TODO: group queries
        try:
            rtype = self._get_rtypes().get(id=rtype_id)
        except RelationType.DoesNotExist as e:
            raise ValidationError(self.error_messages['invalidrtype']) from e

        return rtype

    def _value_from_unjsonfied(self, data):
        all_kwargs = []
        entity_ids = set()  # The queries on CremeEntity are grouped.

        for entry in data:
            kwargs = {'rtype': self._clean_rtype(entry),
                      'has':   self.clean_value(entry, 'has', bool),
                      'ct':    self._clean_ct(entry),
                     }
            entity_id = self._clean_entity_id(entry)

            if entity_id:
                entity_ids.add(entity_id)
                kwargs['entity'] = entity_id

            all_kwargs.append(kwargs)

        if entity_ids:
            entities = CremeEntity.objects.filter(pk__in=entity_ids).in_bulk()

            if len(entities) != len(entity_ids):
                raise ValidationError(self.error_messages['invalidentity'],
                                      code='invalidentity',
                                     )

            for kwargs in all_kwargs:
                entity_id = kwargs.get('entity')
                if entity_id:
                    kwargs['entity'] = entities.get(entity_id)

        build_condition = EntityFilterCondition.build_4_relation

        try:
            conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        RELATION = EntityFilterCondition.EFC_RELATION
        self.initial = [c for c in conditions if c.type == RELATION]


class RelationSubfiltersConditionsField(RelationsConditionsField):
    widget = RelationSubfiltersConditionsWidget
    default_error_messages = {
        'invalidfilter': _('This filter is invalid.'),
    }

    def _condition_to_dict(self, condition):
        value = condition.decoded_value
        filter_id = value['filter_id']

        return {'rtype':  condition.name,
                'has':    boolean_str(value['has']),
                 # TODO: regroup queries ? record in the condition to avoid the query,
                'ctype':  EntityFilter.objects.get(pk=filter_id).entity_type_id,
                'filter': filter_id,
               }

    def _value_from_unjsonfied(self, data):
        all_kwargs = []
        filter_ids = set()  # The queries on EntityFilter are grouped.

        for entry in data:
            kwargs = {'rtype': self._clean_rtype(entry),
                      'has': self.clean_value(entry, 'has', bool),
                     }
            filter_id = self.clean_value(entry, 'filter', str)

            if filter_id:
                filter_ids.add(filter_id)
                kwargs['subfilter'] = filter_id

            all_kwargs.append(kwargs)

        if filter_ids:
            filters = EntityFilter.get_for_user(self.user).filter(pk__in=filter_ids).in_bulk()

            if len(filters) != len(filter_ids):
                raise ValidationError(self.error_messages['invalidfilter'], code='invalidfilter')

            for kwargs in all_kwargs:
                kwargs['subfilter'] = filters.get(kwargs['subfilter'])

        build_condition = EntityFilterCondition.build_4_relation_subfilter

        try:
            conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except EntityFilterCondition.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        RELATION_SUBFILTER = EntityFilterCondition.EFC_RELATION_SUBFILTER
        self.initial = [c for c in conditions if c.type == RELATION_SUBFILTER]


class PropertiesConditionsField(_ConditionsField):
    widget = PropertiesConditionsWidget
    default_error_messages = {
        'invalidptype': _('This property type is invalid with this model.'),
    }

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self.widget.ptypes = CallableChoiceIterator(lambda: [(pt.id, pt) for pt in self._get_ptypes()])

    def _get_ptypes(self):
        return CremePropertyType.objects.compatible(self._model)

    def _value_to_jsonifiable(self, value):
        return [{'ptype': condition.name,
                 'has':   boolean_str(condition.decoded_value),
                } for condition in value
               ]

    def _clean_ptype(self, entry):
        ptype_pk = self.clean_value(entry, 'ptype', str)

        # TODO: regroup queries ??
        try:
            ptype = self._get_ptypes().get(id=ptype_pk)
        except CremePropertyType.DoesNotExist as e:
            raise ValidationError(self.error_messages['invalidptype'], code='invalidptype') from e

        return ptype

    def _value_from_unjsonfied(self, data):
        build = EntityFilterCondition.build_4_property
        clean_ptype = self._clean_ptype
        clean_value = self.clean_value

        return [build(ptype=clean_ptype(entry), has=clean_value(entry, 'has', bool))
                    for entry in data
               ]

    def _set_initial_conditions(self, conditions):
        PROPERTY = EntityFilterCondition.EFC_PROPERTY
        self.initial = [c for c in conditions if c.type == PROPERTY]


# TODO: factorise with _ConditionsField (mixin ?)
class SubfiltersConditionsField(ModelMultipleChoiceField):
    # def __init__(self, model=CremeEntity, *args, **kwargs):
    def __init__(self, *, model=CremeEntity, **kwargs):
        super().__init__(queryset=EntityFilter.objects.none(), **kwargs)

    def clean(self, value):
        build = EntityFilterCondition.build_4_subfilter

        return [build(subfilter) for subfilter in super().clean(value)]

    def initialize(self, ctype, conditions=None, efilter=None):
        qs = EntityFilter.get_for_user(self.user, ctype)

        if efilter:
            qs = qs.exclude(pk__in=efilter.get_connected_filter_ids())

        self.queryset = qs

        if conditions:
            SUBFILTER = EntityFilterCondition.EFC_SUBFILTER
            self.initial = [c.name for c in conditions if c.type == SUBFILTER]


# Forms-------------------------------------------------------------------------

class _EntityFilterForm(CremeModelForm):
    # Notice that we do not use 0/1 because it is linked to a boolean field,
    # so the value given to the widget for the selected choice is 'True' or 'False'...
    use_or = ChoiceField(label=_('The entity is accepted if'),
                         choices=(('False', _('all the conditions are met')),
                                  ('True',  _('any condition is met')),
                                 ),
                         widget=CremeRadioSelect,
                        )

    fields_conditions           = RegularFieldsConditionsField(label=_('On regular fields'), required=False,
                                                               help_text=_('You can write several values, separated by commas.')
                                                              )
    datefields_conditions       = DateFieldsConditionsField(label=_('On date fields'), required=False)
    customfields_conditions     = CustomFieldsConditionsField(label=_('On custom fields'), required=False)
    datecustomfields_conditions = DateCustomFieldsConditionsField(label=_('On date custom fields'), required=False)
    relations_conditions        = RelationsConditionsField(label=_('On relationships'), required=False,
                                                           help_text=_('Do not select any entity if you want to match them all.')
                                                          )
    relsubfilfers_conditions    = RelationSubfiltersConditionsField(label=_('On relationships with results of other filters'), required=False)
    properties_conditions       = PropertiesConditionsField(label=_('On properties'), required=False)
    subfilters_conditions       = SubfiltersConditionsField(label=_('Sub-filters'), required=False)

    error_messages = {
        'no_condition': _('The filter must have at least one condition.'),
    }

    _CONDITIONS_FIELD_NAMES = ('fields_conditions', 'datefields_conditions',
                               'customfields_conditions', 'datecustomfields_conditions',
                               'relations_conditions', 'relsubfilfers_conditions',
                               'properties_conditions', 'subfilters_conditions',
                              )

    blocks = CremeModelForm.blocks.new(('conditions', _('Conditions'), _CONDITIONS_FIELD_NAMES))

    class Meta(CremeModelForm.Meta):
        model = EntityFilter
        help_texts = {
            'user': _('All users can see this filter, but only the owner can edit or delete it'),
            'is_private': _('A private filter can only be used by its owner '
                            '(or the teammates if the owner is a team)'
                           ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].empty_label = _('All users')

    def get_cleaned_conditions(self):
        cdata = self.cleaned_data
        conditions = []

        for fname in self._CONDITIONS_FIELD_NAMES:
            conditions.extend(cdata[fname])

        return conditions

    def clean(self):
        cdata = super().clean()

        if not self._errors:
            if not any(cdata[f] for f in self._CONDITIONS_FIELD_NAMES):
                raise ValidationError(self.error_messages['no_condition'],
                                      code='no_condition',
                                     )

            is_private = cdata.get('is_private', False)
            owner      = cdata.get('user')
            req_user   = self.user

            if not req_user.is_staff and is_private and owner:
                if owner.is_team:
                    if req_user.id not in owner.teammates:
                        self.add_error('user', _('A private filter must belong to you (or one of your teams).'))
                elif owner != req_user:
                    self.add_error('user', _('A private filter must belong to you (or one of your teams).'))

            try:
                self.instance.check_privacy(self.get_cleaned_conditions(), is_private, owner)
            except EntityFilter.PrivacyError as e:
                raise ValidationError(e) from e

        return cdata


class EntityFilterCreateForm(_EntityFilterForm):
    def __init__(self, ctype, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._entity_type = self.instance.entity_type = ctype
        fields = self.fields

        for field_name in self._CONDITIONS_FIELD_NAMES:
            fields[field_name].initialize(ctype)

        fields['use_or'].initial = 'False'

    def save(self, *args, **kwargs):
        instance = self.instance
        ct = self._entity_type

        instance.is_custom = True

        super().save(commit=False, *args, **kwargs)
        generate_string_id_and_save(EntityFilter, [instance],
                                    'creme_core-userfilter_{}-{}'.format(ct.app_label, ct.model),
                                   )

        instance.set_conditions(self.get_cleaned_conditions(),
                                # There cannot be a cycle because we are creating the filter right now
                                check_cycles=False,
                                check_privacy=False,  # Already checked in clean()
                               )

        return instance


class EntityFilterEditForm(_EntityFilterForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance
        args = (instance.entity_type, instance.conditions.all(), instance)

        for field_name in self._CONDITIONS_FIELD_NAMES:
            fields[field_name].initialize(*args)

        if not instance.is_custom:
            del fields['name']
            del fields['is_private']

    def clean(self):
        cdata = super().clean()

        if not self.errors:
            conditions = self.get_cleaned_conditions()

            try:
                self.instance.check_cycle(conditions)
            except EntityFilter.CycleError as e:
                raise ValidationError(e) from e

            cdata['all_conditions'] = conditions

        return cdata

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.set_conditions(self.cleaned_data['all_conditions'],
                                check_cycles=False, check_privacy=False,  # Already checked in clean()
                               )

        return instance
