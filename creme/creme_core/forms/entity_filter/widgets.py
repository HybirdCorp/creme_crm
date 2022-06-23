# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from collections import OrderedDict, defaultdict
from json import dumps as json_dump

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import BooleanField as ModelBooleanField
from django.db.models import DateField as ModelDateField
from django.db.models import DecimalField as ModelDecimalField
from django.db.models import FloatField as ModelFloatField
from django.db.models import IntegerField as ModelIntegerField
from django.db.models.fields.related import RelatedField as ModelRelatedField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_filter import (
    EF_USER,
    _EntityFilterRegistry,
    operators,
)
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import CremeEntity, CustomField
from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.utils.url import TemplateURLBuilder

from ..widgets import (
    ChainedInput,
    DateRangeSelect,
    DynamicInput,
    DynamicSelect,
    DynamicSelectMultiple,
    EntitySelector,
    Label,
    NullableDateRangeSelect,
    PolymorphicInput,
    SelectorList,
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


class FieldConditionSelector(ChainedInput):
    def __init__(
            self,
            model=CremeEntity,
            fields=(),
            operators=(),
            filter_type=EF_USER,
            attrs=None,
            autocomplete=False):
        super().__init__(attrs)
        self.model = model
        self.fields = fields
        self.operators = operators
        self.filter_type = filter_type
        self.autocomplete = autocomplete

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(
            key='${field.type}.${operator.id}',
            attrs={'auto': False},
        )

        EQUALS_OPS = f'{operators.EQUALS}|{operators.EQUALS_NOT}'
        add_input = pinput.add_input
        add_input(
            '^enum(__null)?.({})$'.format(EQUALS_OPS),
            widget=DynamicSelectMultiple, attrs=field_attrs,
            # TODO: use a GET arg instead of using a TemplateURLBuilder ?
            # TODO: remove "field.ctype" ?
            url=TemplateURLBuilder(
                field=(TemplateURLBuilder.Word, '${field.name}'),
            ).resolve(
                'creme_core__enumerable_choices',
                kwargs={'ct_id': ContentType.objects.get_for_model(self.model).id},
            ),
        )

        pinput.add_dselect(
            '^user(__null)?.({})$'.format(EQUALS_OPS),
            '{}?filter_type={}'.format(
                reverse('creme_core__efilter_user_choices'),
                self.filter_type,
            ),
            attrs=field_attrs,
        )
        add_input(
            '^fk(__null)?.({})$'.format(EQUALS_OPS),
            widget=EntitySelector, attrs={'auto': False},
            content_type='${field.ctype}',
        )
        add_input(
            '^date(__null)?.{}$'.format(operators.RANGE),
            widget=NullableDateRangeSelect, attrs={'auto': False},
        )
        add_input(
            '^date(__null)?.({})$'.format(EQUALS_OPS),
            widget=DynamicInput, type='date', attrs={'auto': False},
        )
        add_input(
            '^boolean(__null)?.*', widget=DynamicSelect,
            options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        add_input(
            '(string|.*__null).({})$'.format(operators.ISEMPTY),
            widget=DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    def _build_operatorchoices(self, operators):
        return [
            (
                json_dump({
                    'id': op.type_id,
                    'types': ' '.join(op.allowed_fieldtypes),
                }),
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
            choice_label = f'[{category}] - {subfield.verbose_name}'
            choice_value = {'name': name, 'type': choice_type}

            if choice_type in operators.FIELDTYPES_RELATED:
                choice_value['ctype'] = ContentType.objects.get_for_model(
                    subfield.remote_field.model
                ).id
        else:
            choice_type = self.field_choicetype(field)
            choice_label = field.verbose_name
            choice_value = {'name': name, 'type': choice_type}

            if choice_type in operators.FIELDTYPES_RELATED:
                choice_value['ctype'] = ContentType.objects.get_for_model(
                    field.remote_field.model
                ).id

        return category, (json_dump(choice_value), choice_label)

    def _build_fieldchoices(self, fields):
        categories = defaultdict(list)  # Fields grouped by category (a category by FK)

        for fieldname, fieldlist in fields:
            category, choice = self._build_fieldchoice(fieldname, fieldlist)
            categories[category].append(choice)

        sort_key = collator.sort_key

        return [
            (cat, sorted(categories[cat], key=lambda item: sort_key(item[1])))
            for cat in sorted(categories.keys(), key=sort_key)
        ]

    @staticmethod
    def field_choicetype(field):
        isnull = '__null' if field.null or field.many_to_many else ''

        if isinstance(field, ModelRelatedField):
            if issubclass(field.remote_field.model, get_user_model()):
                return 'user' + isnull

            if (
                not issubclass(field.remote_field.model, CremeEntity)
                # and field.get_tag('enumerable')
                and field.get_tag(FieldTag.ENUMERABLE)
            ):
                return 'enum' + isnull

            return 'fk' + isnull

        if isinstance(field, ModelDateField):
            return 'date' + isnull

        if isinstance(
            field,
            (ModelIntegerField, ModelFloatField, ModelDecimalField),
        ):
            return 'number' + isnull

        if isinstance(field, ModelBooleanField):
            return 'boolean' + isnull

        return 'string'

    def get_context(self, name, value, attrs):
        field_attrs = {'auto': False, 'datatype': 'json'}

        if self.autocomplete:
            field_attrs['autocomplete'] = True

        add_dselect = self.add_dselect
        add_dselect(
            'field',
            options=self._build_fieldchoices(self.fields),
            attrs=field_attrs,
        )
        add_dselect(
            'operator',
            options=self._build_operatorchoices(self.operators),
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


class ConditionListWidget(SelectorList):
    template_name = 'creme_core/forms/widgets/efilter-condition-list.html'
    empty_selector_label = _('No choice available.')

    def get_selector(self, name, value, attrs):
        pass

    def get_context(self, name, value, attrs):
        self.selector = self.get_selector(name, value, attrs)

        if self.selector is None:
            return Label(empty_label=self.empty_selector_label).get_context(
                name=name, value=value, attrs=attrs,
            )

        return super().get_context(name=name, value=value, attrs=attrs)


class RegularFieldsConditionsWidget(ConditionListWidget):
    def __init__(self,
                 model=CremeEntity,
                 fields=(),
                 efilter_registry=None,
                 attrs=None,
                 enabled=True,  # TODO: use
                 ):
        super().__init__(None, attrs)
        self.model = model
        self.fields = fields
        self.efilter_registry = efilter_registry or _EntityFilterRegistry(
            id=-1,
            verbose_name='Default for RegularFieldsConditionsWidget',
        )

    def get_selector(self, name, value, attrs):
        registry = self.efilter_registry

        return FieldConditionSelector(
            model=self.model,
            fields=self.fields,
            operators=[*registry.operators],
            filter_type=registry.id,
            autocomplete=True,
        )


class DateFieldsConditionsWidget(ConditionListWidget):
    # def __init__(self, fields=(), attrs=None, enabled=True):
    def __init__(self, fields=(), attrs=None):
        # super().__init__(None, enabled=enabled, attrs=attrs)
        super().__init__(None, attrs=attrs)
        self.fields = fields

    def _build_fieldchoice(self, name, data):
        field = data[0]
        subfield = data[1] if len(data) > 1 else None

        if subfield is not None:
            category = field.verbose_name
            choice_label = f'[{category}] - {subfield.verbose_name}'  # TODO: factorise
            is_null = subfield.null
        else:
            category = ''
            choice_label = field.verbose_name
            is_null = field.null

        choice_value = {'name': name, 'type': 'daterange__null' if is_null else 'daterange'}
        return category, (json_dump(choice_value), choice_label)

    # TODO: factorise (see FieldConditionSelector)
    def _build_fieldchoices(self, fields):
        categories = defaultdict(list)  # Fields grouped by category (a category by FK)

        for fieldname, fieldlist in fields:
            category, choice = self._build_fieldchoice(fieldname, fieldlist)
            categories[category].append(choice)

        return [
            (cat, sorted(categories[cat], key=lambda item: collator.sort_key(item[1])))
            for cat in sorted(categories.keys(), key=collator.sort_key)
        ]

    def get_selector(self, name, value, attrs):
        fields = [*self.fields]

        if not fields:
            return None

        chained_input = ChainedInput()
        sub_attrs = {'auto': False, 'datatype': 'json'}

        chained_input.add_dselect(
            'field', options=self._build_fieldchoices(fields), attrs=sub_attrs,
        )

        pinput = PolymorphicInput(key='${field.type}', attrs=sub_attrs)
        pinput.add_input('daterange__null', NullableDateRangeSelect, attrs=sub_attrs)
        pinput.add_input('daterange', DateRangeSelect, attrs=sub_attrs)

        chained_input.add_input('range', pinput, attrs=sub_attrs)

        return chained_input


class CustomFieldConditionSelector(FieldConditionSelector):
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
        choice_value = {
            'id':   customfield.id,
            'type': CustomFieldConditionSelector.customfield_choicetype(customfield),
        }

        return '', (json_dump(choice_value), choice_label)

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(key='${field.type}.${operator.id}', attrs={'auto': False})
        pinput.add_input(
            '^enum(__null)?.({}|{})$'.format(operators.EQUALS, operators.EQUALS_NOT),
            widget=DynamicSelectMultiple,
            # TODO: use a GET arg instead of using a TemplateURLBuilder ?
            url=TemplateURLBuilder(
                cf_id=(TemplateURLBuilder.Int, '${field.id}'),
            ).resolve('creme_core__cfield_enums'),
            attrs=field_attrs,
        )
        pinput.add_input(
            '^date(__null)?.{}$'.format(operators.RANGE),
            NullableDateRangeSelect, attrs={'auto': False},
        )
        pinput.add_input(
            '^boolean(__null)?.*',
            DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        pinput.add_input(
            '(string|.*__null)?.({})$'.format(operators.ISEMPTY),
            DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    @staticmethod
    def customfield_choicetype(field):
        return CustomFieldConditionSelector._CHOICETYPES.get(field.field_type, 'string')

    @staticmethod
    def customfield_rname_choicetype(value):
        type_name = value[len('customfield'):]

        if type_name == 'string':
            return 'string'

        if type_name in {'integer', 'double', 'float'}:
            return 'number__null'

        if type_name in {'enum', 'multienum'}:
            return 'enum__null'

        return type_name + '__null'


# TODO: factorise RegularFieldsConditionsWidget ?
class CustomFieldsConditionsWidget(ConditionListWidget):
    empty_selector_label = _('No custom field at present.')

    def __init__(self,
                 fields=(),
                 efilter_registry=None,
                 attrs=None,
                 enabled=True,
                 ):
        super().__init__(None, attrs)
        self.fields = fields
        self.efilter_registry = efilter_registry or _EntityFilterRegistry(
            # id=None,
            id=-1,
            verbose_name='Default for RegularFieldsConditionsWidget',
        )

    def get_selector(self, name, value, attrs):
        fields = [*self.fields]

        if not fields:
            return None

        return CustomFieldConditionSelector(
            fields=fields, autocomplete=True,
            operators=[*self.efilter_registry.operators],
        )


class DateCustomFieldsConditionsWidget(ConditionListWidget):
    empty_selector_label = _('No date custom field at present.')

    # def __init__(self, date_fields_options=(), attrs=None, enabled=True):
    def __init__(self, date_fields_options=(), attrs=None):
        # super().__init__(selector=None, enabled=enabled, attrs=attrs)
        super().__init__(selector=None, attrs=attrs)
        self.date_fields_options = date_fields_options

    def get_selector(self, name, value, attrs):
        options = [*self.date_fields_options]

        if not options:
            return None

        chained_input = ChainedInput()
        sub_attrs = {'auto': False}

        chained_input.add_dselect('field', options=options, attrs=sub_attrs)
        chained_input.add_input('range', NullableDateRangeSelect, attrs=sub_attrs)

        return chained_input


class RelationTargetInput(PolymorphicInput):
    def __init__(self, key='', multiple=False, attrs=None):
        super().__init__(key=key, attrs=attrs)
        self.add_input(
            '^0$', widget=DynamicInput, type='hidden',
            attrs={'auto': False, 'value': '[]'},
        )
        self.set_default_input(
            widget=EntitySelector, attrs={'auto': False, 'multiple': multiple},
        )


class RelationsConditionsWidget(ConditionListWidget):
    def __init__(self, rtypes=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.rtypes = rtypes

    def get_selector(self, name, value, attrs):
        chained_input = ChainedInput()
        rtypes = [*self.rtypes]

        if not rtypes:
            return None

        # datatype = json => boolean are returned as json boolean, not strings
        attrs_json = {'auto': False, 'datatype': 'json'}

        rtype_name = 'rtype'
        # TODO: use a GET arg instead of using a TemplateURLBuilder ?
        ctype_url = TemplateURLBuilder(
            rtype_id=(TemplateURLBuilder.Word, '${%s}' % rtype_name),
        ).resolve('creme_core__ctypes_compatible_with_rtype_as_choices')

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.items(), attrs=attrs_json)
        add_dselect(rtype_name, options=rtypes, attrs={'auto': False, 'autocomplete': True})
        add_dselect('ctype', options=ctype_url, attrs={**attrs_json, 'autocomplete': True})

        chained_input.add_input(
            'entity',
            widget=RelationTargetInput,
            attrs={'auto': False}, key='${ctype}', multiple=True,
        )

        return chained_input


class RelationSubfiltersConditionsWidget(ConditionListWidget):
    empty_selector_label = _('No relation type at present.')

    def __init__(self, rtypes=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.rtypes = rtypes

    def get_selector(self, name, value, attrs):
        chained_input = ChainedInput()
        rtypes = [*self.rtypes]

        if not rtypes:
            return None

        attrs_json = {'auto': False, 'datatype': 'json'}
        rtype_name = 'rtype'
        ctype_name = 'ctype'

        add_dselect = chained_input.add_dselect
        add_dselect('has', options=_HAS_RELATION_OPTIONS.items(), attrs=attrs_json)
        add_dselect(rtype_name, options=rtypes, attrs={'auto': False, 'autocomplete': True})
        add_dselect(
            ctype_name, attrs={**attrs_json, 'autocomplete': True},
            # TODO: use a GET arg instead of using a TemplateURLBuilder ?
            options=TemplateURLBuilder(
                rtype_id=(TemplateURLBuilder.Word, '${%s}' % rtype_name),
            ).resolve('creme_core__ctypes_compatible_with_rtype'),
        )
        add_dselect(
            'filter',
            options=reverse('creme_core__efilters') + '?ct_id=${%s}' % ctype_name,
            attrs={
                'auto': False,
                'autocomplete': True,
                'data-placeholder': _('(no filter)'),
            },
        )

        return chained_input


class PropertiesConditionsWidget(ConditionListWidget):
    def __init__(self, ptypes=(), attrs=None):
        super().__init__(None, attrs=attrs)
        self.ptypes = ptypes

    def get_selector(self, name, value, attrs):
        ptypes = [*self.ptypes]

        if not ptypes:
            return None

        chained_input = ChainedInput(attrs)

        add_dselect = chained_input.add_dselect
        add_dselect(
            'has',
            options=_HAS_PROPERTY_OPTIONS.items(),
            attrs={'auto': False, 'datatype': 'json'},
        )
        add_dselect('ptype', options=ptypes, attrs={'auto': False})

        return chained_input
