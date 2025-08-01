################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from functools import partial
from json import dumps as json_dump
from urllib.parse import urlencode

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
    EF_REGULAR,
    entity_filter_registries,
    operators,
)
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.enumerators import CustomFieldEnumerator
from creme.creme_core.models import CremeEntity, CustomField
from creme.creme_core.models.fields import YearField
from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.utils.url import TemplateURLBuilder

from ..enumerable import (
    EnumerableChoiceSet,
    EnumerableSelect,
    EnumerableSelectMultiple,
    FieldEnumerableChoiceSet,
)
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


class UserEnumerableSelect(EnumerableSelect):
    is_required = True

    def __init__(self, field, filter_type=EF_REGULAR, attrs=None):
        # We avoid early import of the view which breaks some form hooking
        from creme.creme_core.views.entity_filter import (
            EntityFilterUserEnumerator,
        )

        user_ctype = ContentType.objects.get_for_model(field.model)
        uri = reverse(
            'creme_core__efilter_user_choices',
            args=(user_ctype.id, field.name), query={'filter_type': filter_type},
        )

        super().__init__(
            enumerable=EnumerableChoiceSet(
                empty_label=None,
                enumerator=EntityFilterUserEnumerator(
                    field=field,
                    filter_type=filter_type,
                ),
                url=uri,
            ),
            attrs=attrs,
        )


class FieldEnumerableSelect(EnumerableSelectMultiple):
    is_required = True

    def __init__(self, field, attrs=None):
        super().__init__(
            enumerable=FieldEnumerableChoiceSet(
                field=field,
                empty_label=None,
            ),
            attrs=attrs,
        )


class CustomFieldEnumerableSelect(EnumerableSelectMultiple):
    is_required = True

    def __init__(self, custom_field, attrs=None):
        custom_choices_url = reverse('creme_core__cfield_enums', args=(custom_field.id,))

        super().__init__(
            enumerable=EnumerableChoiceSet(
                empty_label=None,
                enumerator=CustomFieldEnumerator(custom_field=custom_field),
                url=custom_choices_url,
            ),
            attrs=attrs,
        )


class FieldConditionSelector(ChainedInput):
    def __init__(self,
                 model=CremeEntity,
                 fields=(),
                 operators=(),
                 filter_type=EF_REGULAR,  # TODO: "efilter_type"?
                 attrs=None,
                 autocomplete=False,
                 ):
        super().__init__(attrs)
        self.model = model
        self.fields = fields
        self.operators = operators
        self.filter_type = filter_type
        self.autocomplete = autocomplete

    def _build_valueinput(self, field_attrs):
        pinput = PolymorphicInput(
            key='${field.type}.${operator.id}.${field.name}',
            attrs={'auto': False},
        )

        EQUALS_OPS = f'{operators.EQUALS}|{operators.EQUALS_NOT}'
        add_input = pinput.add_input

        # json datatype will consider pk strings as an invalid value and replaced
        # by "null"
        enum_field_attrs = {**field_attrs, 'datatype': 'string'}

        def is_enumerable_field(field):
            return isinstance(field, ModelRelatedField) and (
                not issubclass(field.remote_field.model, (CremeEntity, get_user_model()))
                and field.get_tag(FieldTag.ENUMERABLE)
            )

        def is_choices_field(field):
            return not isinstance(field, ModelRelatedField) and field.choices

        for field_info in self.fields:
            name, model_fields = field_info
            field = model_fields[-1]

            if is_enumerable_field(field):
                add_input(
                    f'^enum(__null)?.({EQUALS_OPS}).{name}$',
                    widget=FieldEnumerableSelect, attrs=enum_field_attrs,
                    field=field,
                )
            elif is_choices_field(field):
                add_input(
                    f'^choices(__null)?.({EQUALS_OPS}).{name}$',
                    widget=DynamicSelectMultiple, attrs=enum_field_attrs,
                    options=field.choices,
                )

        user_field = self.model._meta.get_field('user')

        add_input(
            f'^user(__null)?.({EQUALS_OPS}).*$',
            widget=UserEnumerableSelect, attrs={
                **field_attrs,
                # json datatype will consider __operand__ as an invalid value
                # and replaced by "null"
                'datatype': 'string',
            },
            field=user_field,
            filter_type=self.filter_type
        )

        add_input(
            f'^fk(__null)?.({EQUALS_OPS}).*$',
            widget=EntitySelector, attrs={'auto': False},
            content_type='${field.ctype}',
        )
        add_input(
            f'^date(__null)?.{operators.RANGE}.*$',
            widget=NullableDateRangeSelect, attrs={'auto': False},
        )
        add_input(
            f'^date(__null)?.({EQUALS_OPS}).*$',
            widget=DynamicInput, type='date', attrs={'auto': False},
        )
        add_input(
            '^boolean(__null)?.*$', widget=DynamicSelect,
            options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        add_input(
            f'^year(__null)?.{operators.CURRENTYEAR}.*$', widget=DynamicSelect,
            options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        add_input(
            f'(string|.*__null).({operators.ISEMPTY}).*$',
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

    # TODO: better system in core.entity_filter to make this generic
    @staticmethod
    def field_choicetype(field):
        isnull = '__null' if field.null or field.many_to_many else ''

        if isinstance(field, ModelRelatedField):
            if issubclass(field.remote_field.model, get_user_model()):
                return 'user' + isnull

            if (
                not issubclass(field.remote_field.model, CremeEntity)
                and field.get_tag(FieldTag.ENUMERABLE)
            ):
                return 'enum' + isnull

            return 'fk' + isnull

        if field.choices is not None:
            return 'choices' + isnull

        if isinstance(field, ModelDateField):
            return 'date' + isnull

        if isinstance(field, YearField):
            return 'year' + isnull

        if isinstance(
            field,
            (ModelIntegerField, ModelFloatField, ModelDecimalField),
        ):
            return 'number' + isnull

        if isinstance(field, ModelBooleanField):
            return 'boolean' + isnull

        return 'string'

    def get_context(self, name, value, attrs):
        # TODO: the default datatype should be "json" only for JSONField.
        field_attrs = {'auto': False, 'datatype': 'json'}

        if self.autocomplete:
            field_attrs['autocomplete'] = True

        add_dselect = self.add_dselect
        add_dselect(
            'field',
            options=self._build_fieldchoices(self.fields),
            attrs=field_attrs,
            avoid_empty=True,
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
            avoid_empty=True,
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
                 efilter_type: str = EF_REGULAR,
                 attrs=None,
                 enabled=True,  # TODO: use
                 ):
        super().__init__(None, attrs)
        self.model = model
        self.fields = fields
        self.efilter_type = efilter_type

    def get_selector(self, name, value, attrs):
        efilter_type = self.efilter_type

        return FieldConditionSelector(
            model=self.model,
            fields=self.fields,
            filter_type=efilter_type,
            operators=[*entity_filter_registries[efilter_type].operators],
            autocomplete=True,
        )


class DateFieldsConditionsWidget(ConditionListWidget):
    def __init__(self, fields=(), attrs=None):
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
        CustomField.DATE:       'date__null',
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
        pinput = PolymorphicInput(
            key='${field.type}.${operator.id}.${field.id}',
            attrs={'auto': False}
        )

        def is_enumerable_custom_field(field):
            return field.field_type in (CustomField.ENUM, CustomField.MULTI_ENUM)

        for field_info in self.fields:
            field_id, field = field_info

            if is_enumerable_custom_field(field):
                pinput.add_input(
                    f'^enum(__null)?.({operators.EQUALS}|{operators.EQUALS_NOT}).{field_id}$',
                    widget=CustomFieldEnumerableSelect,
                    custom_field=field,
                    attrs=field_attrs,
                )

        pinput.add_input(
            f'^date(__null)?.{operators.RANGE}.*$',
            NullableDateRangeSelect, attrs={'auto': False},
        )
        pinput.add_input(
            '^boolean(__null)?.*',
            DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        pinput.add_input(
            f'(string|.*__null)?.({operators.ISEMPTY}).*$',
            DynamicSelect, options=_BOOL_OPTIONS, attrs=field_attrs,
        )
        pinput.set_default_input(widget=DynamicInput, attrs={'auto': False})

        return pinput

    @staticmethod
    def customfield_choicetype(field):
        return CustomFieldConditionSelector._CHOICETYPES.get(field.field_type, 'string')

    @staticmethod
    def customfield_rname_choicetype(value):
        type_name = value.removeprefix('customfield')

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
                 # efilter_registry=None,
                 efilter_type: str = EF_REGULAR,
                 attrs=None,
                 enabled=True,
                 ):
        super().__init__(None, attrs)
        self.fields = fields
        self.efilter_type = efilter_type

    def get_selector(self, name, value, attrs):
        fields = [*self.fields]

        if not fields:
            return None

        return CustomFieldConditionSelector(
            fields=fields, autocomplete=True,
            operators=[*entity_filter_registries[self.efilter_type].operators],
        )


class DateCustomFieldsConditionsWidget(ConditionListWidget):
    empty_selector_label = _('No date custom field at present.')

    def __init__(self, date_fields_options=(), attrs=None):
        super().__init__(selector=None, attrs=attrs)
        self.date_fields_options = date_fields_options

    def get_selector(self, name, value, attrs):
        options = [*self.date_fields_options]

        if not options:
            return None

        chained_input = ChainedInput()
        sub_attrs = {'auto': False}

        chained_input.add_dselect('field', options=options, attrs=sub_attrs, avoid_empty=True)
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

        add_dselect = partial(
            chained_input.add_dselect,
            avoid_empty=True,
        )
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

    def __init__(self, rtypes=(), efilter_types=(EF_REGULAR,), attrs=None):
        super().__init__(None, attrs=attrs)
        self.rtypes = rtypes
        self.efilter_types = efilter_types

    def get_selector(self, name, value, attrs):
        chained_input = ChainedInput()
        rtypes = [*self.rtypes]

        if not rtypes:
            return None

        attrs_json = {'auto': False, 'datatype': 'json'}
        rtype_name = 'rtype'
        ctype_name = 'ctype'

        add_dselect = partial(chained_input.add_dselect, avoid_empty=True)
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
            options=reverse('creme_core__efilters') + '?' + urlencode(
                {'ct_id': '${%s}' % ctype_name, 'type': self.efilter_types},
                doseq=True, safe='${}',
            ),
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
            avoid_empty=True,
        )
        add_dselect(
            'ptype',
            options=ptypes, attrs={'auto': False},
            avoid_empty=True,
        )

        return chained_input
