# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
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

from typing import (
    Optional, Type,
    Container, Iterable, Iterator,
    Dict, Tuple,
)

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellRegularField,
    EntityCellCustomField,
    EntityCellRelation,
)
from creme.creme_core.models import (
    CremeEntity,
    RelationType,
    CustomField,
    FieldsConfig,
)
from creme.creme_core.utils.meta import (
    ModelFieldEnumerator,
    is_date_field,
)

from creme.reports import constants


class GraphHandCellConstraint:
    type_id: str = ''
    cell_class: Type[EntityCell] = EntityCell

    def __init__(self, model: Type[CremeEntity]):
        self.model = model

    def cells(self, not_hiddable_cell_keys: Container[str] = ()) -> Iterator[EntityCell]:
        raise NotImplementedError()

    def check_cell(self,
                   cell: EntityCell,
                   not_hiddable_cell_keys: Container[str] = ()) -> bool:
        raise NotImplementedError()

    def get_cell(self,
                 cell_key: str,
                 not_hiddable_cell_keys: Container[str] = ()) -> Optional[EntityCell]:
        try:
            cell_type_id, cell_value = cell_key.split('-', 1)
        except ValueError:
            pass
        else:
            cell_cls = self.cell_class

            if cell_type_id == cell_cls.type_id:
                cell = cell_cls.build(self.model, cell_value)

                if cell and self.check_cell(cell, not_hiddable_cell_keys=not_hiddable_cell_keys):
                    return cell

        return None


class GHCCRegularField(GraphHandCellConstraint):
    cell_class = EntityCellRegularField

    def __init__(self, model):
        super().__init__(model=model)
        self.fields_configs = FieldsConfig.LocalCache()

    def _accept_field(self, field, not_hiddable_cell_keys):
        model = field.model

        if self.fields_configs.get_4_model(model).is_field_hidden(field):
            cell = EntityCellRegularField.build(model, field.name)
            return cell.key in not_hiddable_cell_keys

        return True

    def cells(self, not_hiddable_cell_keys=()):
        model = self.model

        for field_chain in ModelFieldEnumerator(
                    model,
                    deep=0,
                    only_leafs=False,
                ).filter(
                    (lambda field, depth: self._accept_field(field, not_hiddable_cell_keys)),
                    viewable=True,
                ):
            yield EntityCellRegularField.build(
                model=model,
                name='__'.join(field.name for field in field_chain),
            )

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        field_info = cell.field_info
        return len(field_info) == 1 and self._accept_field(field_info[0], not_hiddable_cell_keys)


class GHCCRegularFK(GHCCRegularField):
    type_id = 'regular_fk'

    def _accept_field(self, field, not_hiddable_cell_keys):
        # TODO: field.is_relation ??
        # TODO: set the ForeignKeys to entities as not enumerable automatically ?
        if super()._accept_field(field, not_hiddable_cell_keys) and \
           isinstance(field, ForeignKey) and \
           not issubclass(field.remote_field.model, CremeEntity):
            return field.get_tag('enumerable')

        return False


class GHCCRegularDate(GHCCRegularField):
    type_id = 'regular_date'

    def _accept_field(self, field, not_hiddable_cell_keys):
        return super()._accept_field(field, not_hiddable_cell_keys) and is_date_field(field)


class GHCCRelation(GraphHandCellConstraint):
    type_id = 'rtype'
    cell_class = EntityCellRelation

    def cells(self, not_hiddable_cell_keys=()):
        model = self.model

        for rtype in RelationType.objects.compatible(model, include_internals=True):
            yield EntityCellRelation(model=model, rtype=rtype)

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        return cell.relation_type.is_compatible(cell.model)


class GHCCCustomField(GraphHandCellConstraint):
    cell_class = EntityCellCustomField
    customfield_type = 0

    def cells(self, not_hiddable_cell_keys=()):
        # TODO: CustomField manager => compatible() ??
        # TODO: can we regroup the queries on CustomField ?? cache per request instead ?
        for cfield in CustomField.objects.filter(
            content_type=ContentType.objects.get_for_model(self.model),
            field_type=self.customfield_type,
        ):
            yield EntityCellCustomField(cfield)

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        return cell.custom_field.field_type == self.customfield_type


class GHCCCustomEnum(GHCCCustomField):
    type_id = 'custom_enum'
    customfield_type = CustomField.ENUM


class GHCCCustomDate(GHCCCustomField):
    type_id = 'custom_date'
    customfield_type = CustomField.DATETIME


class GraphHandConstraintsRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self):
        self._constraints_by_type_id: Dict[str, Type[GraphHandCellConstraint]] = {}
        self._constraints_by_rgtype:  Dict[int, Type[GraphHandCellConstraint]] = {}
        self._param_validators: Dict[int, forms.Field] = {}

    def cell_constraints(self, model: Type[CremeEntity]) -> Iterator[GraphHandCellConstraint]:
        for constraint_class in self._constraints_by_type_id.values():
            yield constraint_class(model)

    def get_constraint_by_rgraph_type(self,
                                      model: Type[CremeEntity],
                                      rgraph_type: int) -> Optional[GraphHandCellConstraint]:
        constraint_class = self._constraints_by_rgtype.get(rgraph_type)
        return constraint_class(model) if constraint_class else None

    def get_parameter_validator(self, rgraph_type: int) -> Optional[forms.Field]:
        return self._param_validators.get(rgraph_type)

    @property
    def parameter_validators(self) -> Iterator[Tuple[int, forms.Field]]:
        return iter(self._param_validators.items())

    def register_cell_constraint(self, *,
                                 constraint_class: Type[GraphHandCellConstraint],
                                 rgraph_types: Iterable[int]) -> 'GraphHandConstraintsRegistry':
        set_constraint_by_type_id = self._constraints_by_type_id.setdefault
        set_constraint_by_rgtype = self._constraints_by_rgtype.setdefault

        for rgtype in rgraph_types:
            if set_constraint_by_type_id(constraint_class.type_id, constraint_class) is not constraint_class:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register_cell_constraint(): '
                    f'a constraint with type_id="{constraint_class.type_id}" is already registered.'
                )

            if set_constraint_by_rgtype(rgtype, constraint_class) is not constraint_class:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register_cell_constraint(): '
                    f'a constraint is already registered for the graph-type "{rgtype}".'
                )

        return self

    def register_parameter_validator(self, *,
                                     rgraph_types: Iterable[int],
                                     formfield: forms.Field) -> 'GraphHandConstraintsRegistry':
        set_validator = self._param_validators.setdefault

        for rgtype in rgraph_types:
            if set_validator(rgtype, formfield) is not formfield:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register_parameter_validator(): '
                    f'the validator "{formfield}" is already registered for '
                    f'the type "{rgtype}".'
                )

        return self

    @property
    def rgraph_types(self) -> Iterator[int]:
        return iter(self._constraints_by_rgtype.keys())


abscissa_constraints = GraphHandConstraintsRegistry(
).register_cell_constraint(
    constraint_class=GHCCRegularFK,
    rgraph_types=[constants.RGT_FK],
).register_cell_constraint(
    constraint_class=GHCCRegularDate,
    rgraph_types=[
        constants.RGT_DAY,
        constants.RGT_MONTH,
        constants.RGT_YEAR,
        constants.RGT_RANGE,
    ],
).register_cell_constraint(
    constraint_class=GHCCRelation,
    rgraph_types=[constants.RGT_RELATION],
).register_cell_constraint(
    constraint_class=GHCCCustomEnum,
    rgraph_types=[constants.RGT_CUSTOM_FK],
).register_cell_constraint(
    constraint_class=GHCCCustomDate,
    rgraph_types=[
        constants.RGT_CUSTOM_DAY,
        constants.RGT_CUSTOM_MONTH,
        constants.RGT_CUSTOM_YEAR,
        constants.RGT_CUSTOM_RANGE,
    ],
).register_parameter_validator(
    rgraph_types=[
        constants.RGT_RANGE,
        constants.RGT_CUSTOM_RANGE,
    ],
    formfield=forms.IntegerField(label=_('Number of days')),
)
