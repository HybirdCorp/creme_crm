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

# TODO: improve operators code and remove lots of hard-coded stuffs here
#       (& in widgets)

import logging
from datetime import date
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import BooleanField as ModelBooleanField
from django.db.models import FileField as ModelFileField
from django.db.models import ForeignKey as ModelForeignKey
from django.db.models.query_utils import Q
from django.forms import DateField, ModelMultipleChoiceField
from django.utils.choices import CallableChoiceIterator
from django.utils.formats import get_format
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_filter import (
    EF_REGULAR,
    EntityFilterRegistry,
    condition_handler,
    entity_filter_registries,
    operators,
)
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeEntity,
    CremePropertyType,
    CustomField,
    CustomFieldBoolean,
    EntityFilter,
    EntityFilterCondition,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.utils.date_range import date_range_registry
from creme.creme_core.utils.meta import is_date_field

from ..fields import JSONField
from . import widgets

logger = logging.getLogger(__name__)


def boolean_str(val):
    return widgets.TRUE if val else widgets.FALSE


class _ConditionsField(JSONField):
    value_type = list
    _model = None

    def __init__(self, *,
                 model: type[CremeEntity] = CremeEntity,
                 efilter_type: str = EF_REGULAR,
                 condition_cls: type[EntityFilterCondition] = EntityFilterCondition,
                 **kwargs):
        """Constructor.

        @param model: Class inheriting <creme_core.models.CremeEntity>.
        @param efilter_type: See <creme_core.models.EntityFilter.filter_type>.
        """
        super().__init__(**kwargs)
        self.model = model
        self.efilter_type = efilter_type
        self.condition_cls = condition_cls

    @property
    def efilter_type(self) -> str:
        return self._efilter_type

    @efilter_type.setter
    def efilter_type(self, value: str) -> None:
        self._efilter_type = self.widget.efilter_type = value

    def initialize(self, ctype, conditions=None, efilter=None):
        if conditions:
            self._set_initial_conditions(conditions)

        self.model = ctype.model_class()

    @property
    def efilter_registry(self) -> EntityFilterRegistry:
        return entity_filter_registries[self.efilter_type]

    @property
    def model(self) -> type[CremeEntity]:
        return self._model

    @model.setter
    def model(self, model: type[CremeEntity]):
        self._model = model

    def _set_initial_conditions(self, conditions):
        pass  # TODO: generic implementation to factorise


class RegularFieldsConditionsField(_ConditionsField):
    widget = widgets.RegularFieldsConditionsWidget
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
        field_hidden = fconfigs.get_for_model(field.model).is_field_hidden(field)
        excluded = self.excluded_fields
        non_hiddable_fnames = self._non_hiddable_fnames

        if (
            field.get_tag(FieldTag.ENUMERABLE)
            and (not field_hidden or fname in non_hiddable_fnames)
        ):
            fields[field.name] = [field]

        is_sfield_hidden = fconfigs.get_for_model(related_model).is_field_hidden

        for subfield in related_model._meta.fields:
            if (
                subfield.get_tag(FieldTag.VIEWABLE)
                and not is_date_field(subfield)
                and not isinstance(subfield, excluded)
            ):
                full_name = f'{fname}__{subfield.name}'

                if (
                    not (field_hidden or is_sfield_hidden(subfield))
                    or full_name in non_hiddable_fnames
                ):
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
            is_field_hidden = fconfigs.get_for_model(model).is_field_hidden
            excluded = self.excluded_fields

            # TODO: use meta.ModelFieldEnumerator (need to be improved for grouped options)
            for field in model._meta.fields:
                if (
                    field.get_tag(FieldTag.VIEWABLE)
                    and not is_date_field(field)
                    and not isinstance(field, excluded)
                ):
                    if isinstance(field, ModelForeignKey):
                        self._build_related_fields(field, fields, fconfigs)
                    elif not is_field_hidden(field) or field.name in non_hiddable_fnames:
                        fields[field.name] = [field]

            for field in model._meta.many_to_many:
                if field.get_tag(FieldTag.VIEWABLE):  # TODO: test not viewable
                    self._build_related_fields(field, fields, fconfigs)

        return self._fields

    def _value_to_jsonifiable(self, value):
        fields = self._get_fields()
        dicts = []
        field_choicetype = widgets.FieldConditionSelector.field_choicetype

        for condition in value:
            error = condition.handler.error
            if error:
                logger.warning('The condition is invalid & so we ignored it: %s', error)
                continue

            search_info = condition.value  # TODO: use condition.handler
            operator_id = search_info['operator']  # condition.handler.operator_id
            operator = self.efilter_registry.get_operator(operator_id)

            field = fields[condition.name][-1]
            field_entry = {'name': condition.name, 'type': field_choicetype(field)}

            # TODO: use polymorphism instead ??
            if isinstance(operator, operators.BooleanOperatorBase):
                values = search_info['values'][0]
            elif isinstance(field, ModelBooleanField):
                values = search_info['values'][0]
            else:
                values = ','.join(str(value) for value in search_info['values'])

            if field_entry['type'] in operators.FIELDTYPES_RELATED:
                field_entry['ctype'] = ContentType.objects.get_for_model(
                    field.remote_field.model
                ).id

            dicts.append({
                'field': field_entry,
                'operator': {
                    'id': operator_id,
                    'types': ' '.join(operator.allowed_fieldtypes),
                },
                'value': values,
            })

        return dicts

    def _clean_fieldname(self, entry):
        clean_value = self.clean_value
        fname = clean_value(
            clean_value(entry, 'field', dict, required_error_key='invalidfield'),
            'name', str, required_error_key='invalidfield',
        )

        if fname not in self._fields:
            raise ValidationError(
                self.error_messages['invalidfield'],
                code='invalidfield',
            )

        return fname

    def _clean_operator_n_values(self, entry):
        clean_value = self.clean_value
        operator_id = clean_value(
            clean_value(entry, 'operator', dict, required_error_key='invalidoperator'),
            'id', int, required_error_key='invalidoperator',
        )

        operator_class = self.efilter_registry.get_operator(operator_id)

        if not operator_class:
            raise ValidationError(
                self.error_messages['invalidoperator'],
                code='invalidoperator',
            )

        if isinstance(operator_class, operators.BooleanOperatorBase):
            values = [
                clean_value(entry, 'value', bool, required_error_key='invalidvalue'),
            ]
        elif entry is None:
            values = self._return_none_or_raise(self.required, 'invalidvalue')
        elif isinstance(entry.get('value'), list):
            values = [
                v
                for v in clean_value(
                    entry, 'value', list, required_error_key='invalidvalue',
                )
                if v
            ]
        elif isinstance(entry.get('value'), bool):
            values = [entry.get('value')]
        else:
            values = [
                v
                for v in clean_value(
                    entry, 'value', str, required_error_key='invalidvalue',
                ).split(',')
                if v
            ]

        return operator_id, values

    def _value_from_unjsonfied(self, data):
        build_condition = partial(
            condition_handler.RegularFieldConditionHandler.build_condition,
            model=self.model,
            user=self.user,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )
        clean_fieldname = self._clean_fieldname
        clean_operator_n_values = self._clean_operator_n_values
        conditions = []
        errors = []
        self._get_fields()  # Build self._fields

        for entry in data:
            try:
                operator, values = clean_operator_n_values(entry)
                condition = build_condition(
                    field_name=clean_fieldname(entry),
                    operator=operator,
                    values=values,
                )
            except condition_handler.FilterConditionHandler.ValueError as e:
                errors.append(str(e))
            else:
                conditions.append(condition)

        if errors:
            raise ValidationError(errors)

        return conditions

    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.RegularFieldConditionHandler.type_id
        self.initial = f_conds = [c for c in conditions if c.type == type_id]
        self._non_hiddable_fnames = {c.name for c in f_conds}


class DateFieldsConditionsField(_ConditionsField):
    widget: type[widgets.ConditionListWidget] = widgets.DateFieldsConditionsWidget
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
        field_hidden = fconfigs.get_for_model(field.model).is_field_hidden(field)
        is_sfield_hidden = fconfigs.get_for_model(related_model).is_field_hidden
        non_hiddable_fnames = self._non_hiddable_fnames

        for subfield in related_model._meta.fields:
            if subfield.get_tag(FieldTag.VIEWABLE) and is_date_field(subfield):
                full_name = f'{fname}__{subfield.name}'

                if (
                    not (field_hidden or is_sfield_hidden(subfield))
                    or full_name in non_hiddable_fnames
                ):
                    fields[full_name] = [field, subfield]

    # TODO: factorise with RegularFieldsConditionsField
    @_ConditionsField.model.setter
    def model(self, model):
        if self._model != model:
            self._model = model
            self._fields = None  # Clear cache

            self.widget.fields = CallableChoiceIterator(
                lambda: self._get_fields().items()
            )

    def _get_fields(self):
        if self._fields is None:
            self._fields = fields = {}
            model = self.model
            non_hiddable_fnames = self._non_hiddable_fnames
            fconfigs = FieldsConfig.LocalCache()
            is_field_hidden = fconfigs.get_for_model(model).is_field_hidden

            # TODO: use meta.ModelFieldEnumerator (need to be improved for grouped options)
            for field in model._meta.fields:
                if field.get_tag(FieldTag.VIEWABLE):
                    if isinstance(field, ModelForeignKey):
                        self._build_related_fields(field, fields, fconfigs)
                    elif (
                        is_date_field(field)
                        and (not is_field_hidden(field) or field.name in non_hiddable_fnames)
                    ):
                        fields[field.name] = [field]

            for field in model._meta.many_to_many:
                self._build_related_fields(field, fields, fconfigs)  # TODO: test

        return self._fields

    def _format_date(self, date_dict) -> str:
        """@param date_dict: dict (like {"year": 2011, "month": 7, "day": 25}) or None."""
        if date_dict:
            date_obj = date(**date_dict)
            return date_obj.strftime(get_format('DATE_INPUT_FORMATS')[0])

        return ''

    # TODO: factorise with RegularFieldsConditionsField
    def _value_to_jsonifiable(self, value):
        fields = self._get_fields()
        dicts = []
        fmt = self._format_date

        for condition in value:
            error = condition.handler.error
            if error:
                logger.warning('The condition is invalid & so we ignored it: %s', error)
                continue

            get = condition.value.get
            field = fields[condition.name][-1]

            dicts.append({
                'field': {
                    'name': condition.name,
                    'type': 'daterange__null' if field.null else 'daterange',
                },
                'range': {
                    'type':  get('name', ''),
                    'start': fmt(get('start')),
                    'end':   fmt(get('end')),
                },
            })

        return dicts

    def _clean_date_range(self, entry):
        range_info = entry.get('range')

        if not isinstance(range_info, dict):
            raise ValidationError(
                self.error_messages['invalidformat'], code='invalidformat',
            )

        range_type = range_info.get('type') or None
        start = None
        end   = None

        if not range_type:
            start_str = range_info.get('start')
            end_str   = range_info.get('end')

            if not start_str and not end_str:
                raise ValidationError(
                    self.error_messages['emptydates'], code='emptydates',
                )

            clean_date = DateField().clean

            if start_str:
                start = clean_date(start_str)

            if end_str:
                end = clean_date(end_str)
        elif not date_range_registry.get_range(name=range_type):
            raise ValidationError(
                self.error_messages['invaliddaterange'], code='invaliddaterange',
            )

        return (range_type, start, end)

    def _clean_field_name(self, entry):
        clean_value = self.clean_value
        fname = clean_value(
            clean_value(entry, 'field', dict, required_error_key='invalidfield'),
            'name', str, required_error_key='invalidfield',
        )

        if fname not in self._get_fields():
            raise ValidationError(
                self.error_messages['invalidfield'], code='invalidfield',
            )

        return fname

    # TODO: move more validation code to handler
    #  + prefix error message by "Condition on field «{field}»: "
    def _value_from_unjsonfied(self, data):
        build_condition = partial(
            condition_handler.DateRegularFieldConditionHandler.build_condition,
            model=self.model,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )
        clean_field_name = self._clean_field_name
        clean_date_range = self._clean_date_range
        conditions = []
        errors = []

        for entry in data:
            try:
                date_range, start, end = clean_date_range(entry)
                condition = build_condition(
                    field_name=clean_field_name(entry),
                    date_range=date_range, start=start, end=end,
                )
            except ValidationError as e:
                errors.append(e)
            except condition_handler.FilterConditionHandler.ValueError as e:
                errors.append(str(e))
            else:
                conditions.append(condition)

        if errors:
            raise ValidationError(errors)

        return conditions

    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.DateRegularFieldConditionHandler.type_id
        self.initial = f_conds = [c for c in conditions if c.type == type_id]
        self._non_hiddable_fnames = {c.name for c in f_conds}


class CustomFieldsConditionsField(_ConditionsField):
    widget = widgets.CustomFieldsConditionsWidget
    default_error_messages = {
        'invalidcustomfield': _('This custom field is invalid with this model.'),
        'invalidoperator':    _('This operator is invalid.'),
        'invalidvalue':       _('This value is invalid.'),
    }

    # TODO: way to express is_date_customfield()?
    _NOT_ACCEPTED_TYPES = frozenset((CustomField.DATE, CustomField.DATETIME))
    _non_hiddable_cfield_uuids = ()

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self.widget.fields = CallableChoiceIterator(
            lambda: [(cf.id, cf) for cf in self._get_cfields()]
        )

    def _get_cfields(self):
        return CustomField.objects.compatible(
            self._model,
        ).exclude(
            field_type__in=self._NOT_ACCEPTED_TYPES,
        ).filter(
            Q(is_deleted=False) | Q(uuid__in=self._non_hiddable_cfield_uuids)
        )

    def _value_to_jsonifiable(self, value):
        dicts = []
        customfield_rname_choicetype = \
            widgets.CustomFieldConditionSelector.customfield_rname_choicetype
        get_op = self.efilter_registry.get_operator

        for condition in value:
            search_info = condition.value
            operator_id = search_info['operator']
            operator = get_op(operator_id)

            field_type = customfield_rname_choicetype(search_info['rname'])
            field_entry = {'id': condition.handler.custom_field.id, 'type': field_type}

            value = ','.join(str(v) for v in search_info['values'])

            # HACK : lower serialisation of boolean (combobox waiting for 'true' and not 'True')
            if search_info['rname'] == CustomFieldBoolean.get_related_name():
                value = value.lower()

            dicts.append({
                'field':    field_entry,
                'operator': {
                    'id': operator_id,
                    'types': ' '.join(operator.allowed_fieldtypes),
                },
                'value':    value,
            })

        return dicts

    def _clean_custom_field(self, entry):
        clean_value = self.clean_value
        cfield_id = clean_value(
            clean_value(
                entry, 'field', dict,
                required_error_key='invalidcustomfield',
            ),
            'id', int, required_error_key='invalidcustomfield',
        )

        # TODO: regroup queries
        try:
            cfield = self._get_cfields().get(id=cfield_id)
        except CustomField.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['invalidcustomfield'],
                code='invalidcustomfield',
            ) from e

        return cfield

    def _clean_operator_n_values(self, entry):
        clean_value = self.clean_value
        operator_id = clean_value(
            clean_value(
                entry, 'operator', dict,
                required_error_key='invalidoperator',
            ),
            'id', int, required_error_key='invalidoperator',
        )

        operator_class = self.efilter_registry.get_operator(operator_id)

        if not operator_class:
            raise ValidationError(
                self.error_messages['invalidoperator'],
                code='invalidoperator',
            )

        if isinstance(operator_class, operators.BooleanOperatorBase):
            values = [clean_value(entry, 'value', bool, required_error_key='invalidvalue')]
        elif entry is None:
            values = self._return_none_or_raise(self.required, 'invalidvalue')
        elif isinstance(entry.get('value'), list):
            values = [
                v
                for v in clean_value(
                    entry, 'value', list, required_error_key='invalidvalue',
                )
                if v
            ]
        elif isinstance(entry.get('value'), bool):
            values = [entry.get('value')]
        else:
            values = [
                v
                for v in clean_value(
                    entry, 'value', str, required_error_key='invalidvalue',
                ).split(',')
                if v
            ]

        return operator_id, values

    def _value_from_unjsonfied(self, data):
        build_condition = partial(
            condition_handler.CustomFieldConditionHandler.build_condition,
            user=self.user,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )
        clean_cfield = self._clean_custom_field
        clean_operator_n_values = self._clean_operator_n_values
        conditions = []
        errors = []

        for entry in data:
            try:
                operator, values = clean_operator_n_values(entry)
                condition = build_condition(
                    custom_field=clean_cfield(entry),
                    operator=operator,
                    values=values,
                )
            except condition_handler.FilterConditionHandler.ValueError as e:
                errors.append(str(e))
            else:
                conditions.append(condition)

        if errors:
            raise ValidationError(errors)

        return conditions

    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.CustomFieldConditionHandler.type_id
        filtered_conds = [c for c in conditions if c.type == type_id]
        if filtered_conds:
            self.initial = filtered_conds
            self._non_hiddable_cfield_uuids = {c.name for c in filtered_conds}


class DateCustomFieldsConditionsField(CustomFieldsConditionsField, DateFieldsConditionsField):
    widget: type[widgets.ConditionListWidget] = widgets.DateCustomFieldsConditionsWidget
    default_error_messages = {
        'invalidcustomfield': _('This date custom field is invalid with this model.'),
    }

    @CustomFieldsConditionsField.model.setter
    def model(self, model):  # TODO: factorise ??
        self._model = model
        self.widget.date_fields_options = CallableChoiceIterator(
            lambda: [(cf.id, cf) for cf in self._get_cfields()]
        )

    # TODO: factorise
    def _get_cfields(self):
        return CustomField.objects.compatible(
            self._model,
        ).filter(
            field_type__in=(CustomField.DATE, CustomField.DATETIME),
        ).filter(
            Q(is_deleted=False) | Q(uuid__in=self._non_hiddable_cfield_uuids)
        )

    def _value_to_jsonifiable(self, value):
        dicts = []
        fmt = self._format_date

        for condition in value:
            get = condition.value.get

            dicts.append({
                'field': condition.handler.custom_field.id,
                'range': {
                    'type':  get('name', ''),
                    'start': fmt(get('start')),
                    'end':   fmt(get('end')),
                },
            })

        return dicts

    def _clean_custom_field(self, entry):
        cfield_id = self.clean_value(entry, 'field', int)

        # TODO: regroup queries
        try:
            cfield = self._get_cfields().get(id=cfield_id)
        except CustomField.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['invalidcustomfield'],
                code='invalidcustomfield',
            ) from e

        return cfield

    def _value_from_unjsonfied(self, data):
        build_condition = partial(
            condition_handler.DateCustomFieldConditionHandler.build_condition,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )
        clean_cfield = self._clean_custom_field
        clean_date_range = self._clean_date_range
        conditions = []
        errors = []

        for entry in data:
            try:
                date_range, start, end = clean_date_range(entry)
                condition = build_condition(
                    custom_field=clean_cfield(entry),
                    date_range=date_range, start=start, end=end,
                )
            except ValidationError as e:
                errors.append(e)
            except condition_handler.FilterConditionHandler.ValueError as e:
                errors.append(str(e))
            else:
                conditions.append(condition)

        if errors:
            raise ValidationError(errors)

        return conditions

    # TODO: factorise
    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.DateCustomFieldConditionHandler.type_id
        filtered_conds = [c for c in conditions if c.type == type_id]
        if filtered_conds:
            self.initial = filtered_conds
            self._non_hiddable_cfield_uuids = {c.name for c in filtered_conds}


class RelationsConditionsField(_ConditionsField):
    widget = widgets.RelationsConditionsWidget
    default_error_messages = {
        'invalidrtype':  _('This type of relationship type is invalid with this model.'),
        'invalidct':     _('This content type is invalid.'),
        'invalidentity': _('This entity is invalid.'),
    }

    _non_hiddable_rtype_ids = ()

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self.widget.rtypes = CallableChoiceIterator(
            lambda: [(rt.id, rt) for rt in self._get_rtypes()]
        )

    def _get_rtypes(self):
        return RelationType.objects.compatible(
            self._model, include_internals=True,
        ).filter(
            Q(enabled=True) | Q(id__in=self._non_hiddable_rtype_ids)
        )

    def _condition_to_dict(self, condition):
        value = condition.value
        ctype = condition.handler.content_type
        ctype_id = ctype.id if ctype else 0

        # TODO: regroup queries....
        entity = condition.handler.entity
        if entity:
            entity_id = entity.id
            ctype_id = entity.entity_type_id
        else:
            entity_id = None

        return {
            'rtype':  condition.name,
            'has':    boolean_str(value['has']),
            'ctype':  ctype_id,
            'entity': entity_id,
        }

    # TODO: test with deleted entity ??
    def _value_to_jsonifiable(self, value):
        return [*map(self._condition_to_dict, value)]

    def _clean_ct(self, entry):
        ct_id = self.clean_value(entry, 'ctype', int)

        if ct_id:
            try:
                ct = ContentType.objects.get_for_id(ct_id)
            except ContentType.DoesNotExist as e:
                raise ValidationError(
                    self.error_messages['invalidct'],
                    code='invalidct',
                ) from e

            return ct

    def _clean_entity_id(self, entry):
        entity_id = entry.get('entity')  # TODO: improve clean_value with default value ???

        if entity_id:
            try:
                return int(entity_id)
            except ValueError as e:
                raise ValidationError(
                    self.error_messages['invalidformat'],
                    code='invalidformat',
                ) from e

    def _clean_rtype(self, entry):
        rtype_id = self.clean_value(entry, 'rtype', str)

        # TODO: group queries
        try:
            rtype = self._get_rtypes().get(id=rtype_id)
        except RelationType.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['invalidrtype'],
                code='invalidrtype',
            ) from e

        return rtype

    def _value_from_unjsonfied(self, data):
        all_kwargs = []
        entity_ids = set()  # The queries on CremeEntity are grouped.

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
            entities = CremeEntity.objects.filter(pk__in=entity_ids).in_bulk()

            if len(entities) != len(entity_ids):
                raise ValidationError(
                    self.error_messages['invalidentity'],
                    code='invalidentity',
                )

            for kwargs in all_kwargs:
                entity_id = kwargs.get('entity')
                if entity_id:
                    kwargs['entity'] = entities.get(entity_id)

        build_condition = partial(
            condition_handler.RelationConditionHandler.build_condition,
            model=self._model,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )

        try:
            conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except condition_handler.FilterConditionHandler.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.RelationConditionHandler.type_id
        self.initial = f_conds = [c for c in conditions if c.type == type_id]
        self._non_hiddable_rtype_ids = {c.name for c in f_conds}


class RelationSubfiltersConditionsField(RelationsConditionsField):
    widget = widgets.RelationSubfiltersConditionsWidget
    sub_filter_types = [EF_REGULAR]
    default_error_messages = {
        'invalidfilter': _('This filter is invalid.'),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.widget.efilter_types = self.sub_filter_types

    def _condition_to_dict(self, condition):
        value = condition.value
        filter_id = value['filter_id']

        return {
            'rtype':  condition.name,
            'has':    boolean_str(value['has']),
            # TODO: regroup queries ? record in the condition to avoid the query
            'ctype':  EntityFilter.objects.get(pk=filter_id).entity_type_id,
            'filter': filter_id,
        }

    def _value_from_unjsonfied(self, data):
        all_kwargs = []
        filter_ids = set()  # The queries on EntityFilter are grouped.

        for entry in data:
            kwargs = {
                'rtype': self._clean_rtype(entry),
                'has': self.clean_value(entry, 'has', bool),
            }
            filter_id = self.clean_value(entry, 'filter', str)

            if filter_id:
                filter_ids.add(filter_id)
                kwargs['subfilter'] = filter_id

            all_kwargs.append(kwargs)

        if filter_ids:
            filters = EntityFilter.objects.filter_by_user(
                self.user, types=self.sub_filter_types,
            ).filter(pk__in=filter_ids).in_bulk()

            if len(filters) != len(filter_ids):
                raise ValidationError(
                    self.error_messages['invalidfilter'],
                    code='invalidfilter',
                )

            for kwargs in all_kwargs:
                kwargs['subfilter'] = filters.get(kwargs['subfilter'])

        build_condition = partial(
            condition_handler.RelationSubFilterConditionHandler.build_condition,
            model=self._model,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )

        try:
            conditions = [build_condition(**kwargs) for kwargs in all_kwargs]
        except condition_handler.FilterConditionHandler.ValueError as e:
            raise ValidationError(str(e)) from e

        return conditions

    # TODO: factorise with RelationsConditionsField
    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.RelationSubFilterConditionHandler.type_id
        self.initial = f_conds = [c for c in conditions if c.type == type_id]
        self._non_hiddable_rtype_ids = {c.name for c in f_conds}


class PropertiesConditionsField(_ConditionsField):
    widget = widgets.PropertiesConditionsWidget
    default_error_messages = {
        'invalidptype': _('This property type is invalid with this model.'),
    }

    _non_disabled_ptype_uuids = ()

    @_ConditionsField.model.setter
    def model(self, model):
        self._model = model
        self.widget.ptypes = CallableChoiceIterator(
            lambda: [(pt.id, pt) for pt in self._get_ptypes()]
        )

    def _get_ptypes(self):
        return CremePropertyType.objects.compatible(self._model).filter(
            Q(enabled=True) | Q(uuid__in=self._non_disabled_ptype_uuids)
        )

    def _value_to_jsonifiable(self, value):
        return [
            {
                'ptype': condition.name,
                'has':   boolean_str(condition.value['has']),
            } for condition in value
        ]

    def _clean_ptype(self, entry):
        ptype_pk = self.clean_value(entry, 'ptype', str)

        # TODO: regroup queries ??
        try:
            ptype = self._get_ptypes().get(id=ptype_pk)
        except CremePropertyType.DoesNotExist as e:
            raise ValidationError(
                self.error_messages['invalidptype'],
                code='invalidptype',
            ) from e

        return ptype

    def _value_from_unjsonfied(self, data):
        build_condition = partial(
            condition_handler.PropertyConditionHandler.build_condition,
            model=self._model,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )
        clean_ptype = self._clean_ptype
        clean_value = self.clean_value

        return [
            build_condition(
                ptype=clean_ptype(entry),
                has=clean_value(entry, 'has', bool),
            ) for entry in data
        ]

    def _set_initial_conditions(self, conditions):
        type_id = condition_handler.PropertyConditionHandler.type_id
        self.initial = f_conds = [c for c in conditions if c.type == type_id]
        self._non_disabled_ptype_uuids = {c.name for c in f_conds}


# TODO: factorise with _ConditionsField (mixin ?)
class SubfiltersConditionsField(ModelMultipleChoiceField):
    sub_filter_types = [EF_REGULAR]  # TODO: pass to  __init__?

    def __init__(self, *,
                 model=CremeEntity,
                 efilter_type: str = EF_REGULAR,
                 condition_cls=EntityFilterCondition,
                 user=None,
                 **kwargs):
        super().__init__(queryset=EntityFilter.objects.none(), **kwargs)
        self.user = user
        self.model = model
        self.efilter_type = efilter_type
        self.condition_cls = condition_cls

    @property
    def efilter_type(self):
        return self._efilter_type

    @efilter_type.setter
    def efilter_type(self, value: str):
        self._efilter_type = value

    @property
    def efilter_registry(self):
        return entity_filter_registries[self.efilter_type]

    def clean(self, value):
        build_condition = partial(
            condition_handler.SubFilterConditionHandler.build_condition,
            condition_cls=self.condition_cls,
            filter_type=self.efilter_type,
        )

        return [build_condition(subfilter) for subfilter in super().clean(value)]

    def initialize(self, ctype, conditions=None, efilter=None):
        qs = EntityFilter.objects.filter_by_user(
            self.user, types=self.sub_filter_types,
        ).filter(entity_type=ctype)

        if efilter:
            qs = qs.exclude(pk__in=efilter.get_connected_filter_ids())

        self.queryset = qs

        if conditions:
            type_id = condition_handler.SubFilterConditionHandler.type_id
            self.initial = [c.name for c in conditions if c.type == type_id]
