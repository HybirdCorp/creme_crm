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
import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    DateField as ModelDateField,
    IntegerField as ModelIntegerField,
    FloatField as ModelFloatField,
    DecimalField as ModelDecimalField,
    BooleanField as ModelBooleanField,
)
from django.db.models.fields.related import RelatedField as ModelRelatedField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_filter import (
    _EntityFilterRegistry,
    operators,
)
from creme.creme_core.models import CremeEntity, CustomField  # EntityFilterCondition
from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.utils.url import TemplateURLBuilder

from ..widgets import (
    DynamicInput, SelectorList, ChainedInput, Label,
    EntitySelector, DateRangeSelect,
    DynamicSelect, DynamicSelectMultiple, PolymorphicInput,
    NullableDateRangeSelect,
)

TRUE = 'true'
FALSE = 'false'

_BOOL_OPTIONS = (
    (TRUE,  _('True')),
    (FALSE, _('False')),
)
_HAS_PROPERTY_OPTIONS = OrderedDict([
    (TRUE,  _('Has the property')),
    (FALSE, _('Does not have the property')),
])
_HAS_RELATION_OPTIONS = OrderedDict([
    (TRUE,  _('Has the relationship')),
    (FALSE, _('Does not have the relationship')),
])


class FieldConditionWidget(ChainedInput):  # TODO: rename FieldConditionSelector ??
    def __init__(self, model=CremeEntity, fields=(), operators=(), attrs=None, autocomplete=False):
        super().__init__(attrs)
        self.model = model
        self.fields = fields
        self.operators = operators
        self.autocomplete = autocomplete

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(key='${field.type}.${operator.id}', attrs={'auto': False})

        # EQUALS_OPS = '{}|{}'.format(EntityFilterCondition.EQUALS, EntityFilterCondition.EQUALS_NOT)
        EQUALS_OPS = '{}|{}'.format(operators.EQUALS, operators.EQUALS_NOT)
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
        # add_input('^date(__null)?.{}$'.format(EntityFilterCondition.RANGE),
        add_input('^date(__null)?.{}$'.format(operators.RANGE),
                  widget=DateRangeSelect, attrs={'auto': False},
                 )
        add_input('^boolean(__null)?.*', widget=DynamicSelect,
                  options=_BOOL_OPTIONS, attrs=field_attrs,
                 )
        # add_input('(string|.*__null).({})$'.format(EntityFilterCondition.ISEMPTY),
        add_input('(string|.*__null).({})$'.format(operators.ISEMPTY),
                  widget=DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
                 )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    def _build_operatorchoices(self, operators):
        # return [
        #     (json.dumps({'id': id, 'types': ' '.join(op.allowed_fieldtypes)}),
        #      op.name,
        #     ) for id, op in operators.items()
        # ]
        return [
            (json.dumps({'id': op.type_id, 'types': ' '.join(op.allowed_fieldtypes)}),
             op.verbose_name,
            ) for op in operators
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

            # if choice_type in EntityFilterCondition._FIELDTYPES_RELATED:
            if choice_type in operators.FIELDTYPES_RELATED:
                choice_value['ctype'] = ContentType.objects.get_for_model(subfield.remote_field.model).id
        else:
            choice_type = self.field_choicetype(field)
            choice_label = field.verbose_name
            choice_value = {'name': name, 'type': choice_type}

            # if choice_type in EntityFilterCondition._FIELDTYPES_RELATED:
            if choice_type in operators.FIELDTYPES_RELATED:
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
    # def __init__(self, model=CremeEntity, fields=(), attrs=None, enabled=True):
    def __init__(self, model=CremeEntity, fields=(), efilter_registry=None,
                 attrs=None, enabled=True):  # TODO: use 'enabled'
        super().__init__(None, attrs)
        self.model = model
        self.fields = fields
        self.efilter_registry = efilter_registry or _EntityFilterRegistry()

    def get_context(self, name, value, attrs):
        self.selector = FieldConditionWidget(
            model=self.model,
            fields=self.fields,
            # operators=EntityFilterCondition._OPERATOR_MAP,
            operators=[*self.efilter_registry.operators],
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
        # pinput.add_input('^enum(__null)?.({}|{})$'.format(EntityFilterCondition.EQUALS,
        #                                                   EntityFilterCondition.EQUALS_NOT,
        #                                                  ),
        pinput.add_input('^enum(__null)?.({}|{})$'.format(operators.EQUALS,
                                                          operators.EQUALS_NOT,
                                                         ),
                         widget=DynamicSelectMultiple,
                         # TODO: use a GET arg instead of using a TemplateURLBuilder ?
                         url=TemplateURLBuilder(cf_id=(TemplateURLBuilder.Int, '${field.id}'))
                                               .resolve('creme_core__cfield_enums'),
                         attrs=field_attrs,
                        )
        # pinput.add_input('^date(__null)?.{}$'.format(EntityFilterCondition.RANGE),
        pinput.add_input('^date(__null)?.{}$'.format(operators.RANGE),
                         NullableDateRangeSelect, attrs={'auto': False},
                        )
        pinput.add_input('^boolean(__null)?.*',
                         # DynamicSelect, options=((TRUE, _('True')), (FALSE, _('False'))), attrs=field_attrs,
                         DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
                        )
        # pinput.add_input('(string|.*__null)?.({})$'.format(EntityFilterCondition.ISEMPTY),
        pinput.add_input('(string|.*__null)?.({})$'.format(operators.ISEMPTY),
                         # DynamicSelect, options=((TRUE, _('True')), (FALSE, _('False'))), attrs=field_attrs,
                         DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
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

    # def __init__(self, fields=(), attrs=None, enabled=True):
    def __init__(self, fields=(), efilter_registry=None, attrs=None, enabled=True):
        super().__init__(None, attrs)
        self.fields = fields
        self.efilter_registry = efilter_registry or _EntityFilterRegistry()

    def get_context(self, name, value, attrs):
        fields = list(self.fields)

        if not fields:
            return Label(empty_label=_('No custom field at present.'))\
                        .get_context(name=name, value=value, attrs=attrs)

        self.selector = CustomFieldConditionSelector(
            fields=fields, autocomplete=True,
            # TODO: given by form field ?
            # operators=EntityFilterCondition._OPERATOR_MAP,
            operators=[*self.efilter_registry.operators],
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
        self.add_input('^0$', widget=DynamicInput, type='hidden', attrs={'auto': False, 'value': '[]'})
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
