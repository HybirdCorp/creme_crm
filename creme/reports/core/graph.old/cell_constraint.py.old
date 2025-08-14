################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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

from __future__ import annotations

from collections.abc import Collection, Container, Iterable, Iterator

from django import forms
from django.db import models
from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.field_tags import FieldTag
from creme.creme_core.models import (
    CremeEntity,
    CustomField,
    FieldsConfig,
    RelationType,
)
from creme.creme_core.utils.meta import ModelFieldEnumerator, is_date_field
from creme.reports.constants import AbscissaGroup, OrdinateAggregator


class GraphHandCellConstraint:
    type_id: str = ''
    cell_class: type[EntityCell] = EntityCell

    def __init__(self, model: type[CremeEntity]):
        self.model = model

    def cells(self,
              not_hiddable_cell_keys: Container[str] = (),
              ) -> Iterator[EntityCell]:
        raise NotImplementedError

    def check_cell(self,
                   cell: EntityCell,
                   not_hiddable_cell_keys: Container[str] = (),
                   ) -> bool:
        raise NotImplementedError

    def get_cell(self,
                 cell_key: str,
                 not_hiddable_cell_keys: Container[str] = (),
                 ) -> EntityCell | None:
        try:
            cell_type_id, cell_value = cell_key.split('-', 1)
        except ValueError:
            pass
        else:
            cell_cls = self.cell_class

            if cell_type_id == cell_cls.type_id:
                cell = cell_cls.build(self.model, cell_value)

                if cell and self.check_cell(
                    cell, not_hiddable_cell_keys=not_hiddable_cell_keys,
                ):
                    return cell

        return None


class GHCCRegularField(GraphHandCellConstraint):
    cell_class = EntityCellRegularField

    def __init__(self, model):
        super().__init__(model=model)
        self.fields_configs = FieldsConfig.LocalCache()

    def _accept_field(self, field, not_hiddable_cell_keys):
        model = field.model

        if not field.get_tag(FieldTag.VIEWABLE):  # TODO: test
            return False

        if self.fields_configs.get_for_model(model).is_field_hidden(field):
            cell = EntityCellRegularField.build(model, field.name)
            return cell.key in not_hiddable_cell_keys

        return True

    def cells(self, not_hiddable_cell_keys=()):
        model = self.model

        for field_chain in ModelFieldEnumerator(
            model, depth=0, only_leaves=False,
        ).filter(
            lambda model, field, depth: self._accept_field(field, not_hiddable_cell_keys),
        ):
            yield EntityCellRegularField.build(
                model=model,
                name='__'.join(field.name for field in field_chain),
            )

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        field_info = cell.field_info
        return (
            len(field_info) == 1
            and self._accept_field(field_info[0], not_hiddable_cell_keys)
        )


class GHCCRegularFK(GHCCRegularField):
    type_id = 'regular_fk'

    def _accept_field(self, field, not_hiddable_cell_keys):
        # TODO: field.is_relation ??
        # TODO: set the ForeignKeys to entities as not enumerable automatically ?
        if (
            super()._accept_field(field, not_hiddable_cell_keys)
            and isinstance(field, ForeignKey)
            and not issubclass(field.remote_field.model, CremeEntity)
        ):
            return field.get_tag(FieldTag.ENUMERABLE)

        return False


class GHCCRegularChoices(GHCCRegularField):
    type_id = 'regular_choices'

    def _accept_field(self, field, not_hiddable_cell_keys):
        return (
            super()._accept_field(field, not_hiddable_cell_keys)  # TODO: test
            and field.choices is not None
        )


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
            cell = EntityCellRelation(model=model, rtype=rtype)

            if self.check_cell(cell=cell, not_hiddable_cell_keys=not_hiddable_cell_keys):
                yield cell

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        rtype = cell.relation_type

        return (
            (rtype.enabled or cell.key in not_hiddable_cell_keys)
            and rtype.is_compatible(cell.model)
        )


class GHCCCustomField(GraphHandCellConstraint):
    cell_class = EntityCellCustomField
    customfield_types: set[int] = set()

    def cells(self, not_hiddable_cell_keys=()):
        for cfield in CustomField.objects.get_for_model(self.model).values():
            cell = EntityCellCustomField(cfield)

            if self.check_cell(cell=cell, not_hiddable_cell_keys=not_hiddable_cell_keys):
                yield cell

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        cfield = cell.custom_field

        return (
            (not cfield.is_deleted or cell.key in not_hiddable_cell_keys)
            and cfield.field_type in self.customfield_types
        )


class GHCCCustomEnum(GHCCCustomField):
    type_id = 'custom_enum'
    customfield_types = {CustomField.ENUM}


class GHCCCustomDate(GHCCCustomField):
    type_id = 'custom_date'
    customfield_types = {CustomField.DATE, CustomField.DATETIME}


class GraphHandConstraintsRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self) -> None:
        self._constraints_by_type_id: dict[str, type[GraphHandCellConstraint]] = {}
        self._constraints_by_rgtype:  dict[int, type[GraphHandCellConstraint]] = {}
        self._param_validators: dict[int, forms.Field] = {}

    def cell_constraints(self,
                         model: type[CremeEntity],
                         ) -> Iterator[GraphHandCellConstraint]:
        for constraint_class in self._constraints_by_type_id.values():
            yield constraint_class(model)

    def get_constraint_by_rgraph_type(self,
                                      model: type[CremeEntity],
                                      rgraph_type: int,
                                      ) -> GraphHandCellConstraint | None:
        constraint_class = self._constraints_by_rgtype.get(rgraph_type)
        return constraint_class(model) if constraint_class else None

    def get_parameter_validator(self, rgraph_type: int) -> forms.Field | None:
        return self._param_validators.get(rgraph_type)

    @property
    def parameter_validators(self) -> Iterator[tuple[int, forms.Field]]:
        return iter(self._param_validators.items())

    def register_cell_constraint(self, *,
                                 constraint_class: type[GraphHandCellConstraint],
                                 rgraph_types: Iterable[int],
                                 ) -> GraphHandConstraintsRegistry:
        set_constraint_by_type_id = self._constraints_by_type_id.setdefault
        set_constraint_by_rgtype = self._constraints_by_rgtype.setdefault

        for rgtype in rgraph_types:
            if set_constraint_by_type_id(
                    constraint_class.type_id, constraint_class,
            ) is not constraint_class:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register_cell_constraint(): '
                    f'a constraint with type_id="{constraint_class.type_id}" '
                    f'is already registered.'
                )

            if set_constraint_by_rgtype(rgtype, constraint_class) is not constraint_class:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register_cell_constraint(): '
                    f'a constraint is already registered for the graph-type "{rgtype}".'
                )

        return self

    def register_parameter_validator(self, *,
                                     rgraph_types: Iterable[int],
                                     formfield: forms.Field,
                                     ) -> GraphHandConstraintsRegistry:
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
    rgraph_types=[AbscissaGroup.FK],
).register_cell_constraint(
    constraint_class=GHCCRegularChoices,
    rgraph_types=[AbscissaGroup.CHOICES],
).register_cell_constraint(
    constraint_class=GHCCRegularDate,
    rgraph_types=[
        AbscissaGroup.DAY,
        AbscissaGroup.MONTH,
        AbscissaGroup.YEAR,
        AbscissaGroup.RANGE,
    ],
).register_cell_constraint(
    constraint_class=GHCCRelation,
    rgraph_types=[AbscissaGroup.RELATION],
).register_cell_constraint(
    constraint_class=GHCCCustomEnum,
    rgraph_types=[AbscissaGroup.CUSTOM_FK],
).register_cell_constraint(
    constraint_class=GHCCCustomDate,
    rgraph_types=[
        AbscissaGroup.CUSTOM_DAY,
        AbscissaGroup.CUSTOM_MONTH,
        AbscissaGroup.CUSTOM_YEAR,
        AbscissaGroup.CUSTOM_RANGE,
    ],
).register_parameter_validator(
    rgraph_types=[
        AbscissaGroup.RANGE,
        AbscissaGroup.CUSTOM_RANGE,
    ],
    formfield=forms.IntegerField(label=_('Number of days')),
)


# ------------------------------------------------------------------------------
class AggregatorCellConstraint:
    type_id: str = ''
    aggregator_ids: Collection[str] = []
    cell_classes: Collection[type[EntityCell]] = []

    def __init__(self, model: type[CremeEntity]):
        self.model = model

    def cells(self,
              not_hiddable_cell_keys: Container[str] = (),
              ) -> Iterator[EntityCell]:
        yield from ()

    def check_cell(self,
                   cell: EntityCell,
                   not_hiddable_cell_keys: Container[str] = (),
                   ) -> bool:
        return True

    def get_cell(self,
                 cell_key: str,
                 not_hiddable_cell_keys: Container[str] = (),
                 check: bool = True,
                 ) -> EntityCell | None:
        try:
            cell_type_id, cell_value = cell_key.split('-', 1)
        except ValueError:
            pass
        else:
            for cell_cls in self.cell_classes:
                if cell_type_id == cell_cls.type_id:
                    cell = cell_cls.build(self.model, cell_value)

                    if not check:
                        return cell

                    return (
                        cell
                        if cell and self.check_cell(
                            cell,
                            not_hiddable_cell_keys=not_hiddable_cell_keys,
                        ) else
                        None
                    )

        return None


class ACCCount(AggregatorCellConstraint):
    type_id = 'count'
    aggregator_ids = [OrdinateAggregator.COUNT]


class ACCFieldAggregation(AggregatorCellConstraint):
    type_id = 'field_aggregation'
    aggregator_ids = [
        OrdinateAggregator.AVG,
        OrdinateAggregator.MAX,
        OrdinateAggregator.MIN,
        OrdinateAggregator.SUM,
    ]
    cell_classes: list[type[EntityCell]] = [
        EntityCellRegularField,
        EntityCellCustomField,
    ]

    model_field_classes: tuple[models.Field, ...] = (
        models.IntegerField,
        models.DecimalField,
        models.FloatField,
    )
    custom_field_types: tuple[int, ...] = (
        CustomField.INT,
        CustomField.FLOAT,
    )

    def __init__(self, model):
        super().__init__(model=model)
        self.fields_configs = FieldsConfig.LocalCache()

    def _accept_cfield(self, cfield, not_hiddable_cell_keys):
        if cfield.field_type not in self.custom_field_types:
            return False

        if cfield.is_deleted:
            cell = EntityCellCustomField(cfield)
            return cell.key in not_hiddable_cell_keys

        return True

    def _accept_rfield(self, field, not_hiddable_cell_keys):
        # TODO: take model as parameter because field.model could refer the
        #       parent class if the field is inherited (currently only "description")
        model = field.model

        if not isinstance(field, self.model_field_classes):
            return False

        if not field.get_tag(FieldTag.VIEWABLE):  # TODO: test
            return False

        if self.fields_configs.get_for_model(model).is_field_hidden(field):
            cell = EntityCellRegularField.build(model, field.name)
            return cell.key in not_hiddable_cell_keys

        return True

    def _cfield_cells(self, not_hiddable_cell_keys=()):
        types = self.custom_field_types

        if types:  # NB: avoid useless query if types is empty
            accept = self._accept_cfield

            for cfield in CustomField.objects.get_for_model(self.model).values():
                if accept(cfield, not_hiddable_cell_keys=not_hiddable_cell_keys):
                    yield EntityCellCustomField(cfield)

    def _rfield_cells(self, not_hiddable_cell_keys=()):
        model = self.model

        for field_chain in ModelFieldEnumerator(
            self.model, depth=0,
        ).filter(
            lambda model, field, depth: self._accept_rfield(field, not_hiddable_cell_keys)
        ):
            yield EntityCellRegularField.build(
                model=model,
                name='__'.join(field.name for field in field_chain),
            )

    def cells(self, not_hiddable_cell_keys=()):
        yield from self._rfield_cells(not_hiddable_cell_keys)
        yield from self._cfield_cells(not_hiddable_cell_keys)

    def check_cell(self, cell, not_hiddable_cell_keys=()):
        if isinstance(cell, EntityCellRegularField):
            field_info = cell.field_info

            return (
                len(field_info) == 1
                and self._accept_rfield(field_info[0], not_hiddable_cell_keys)
            )

        if isinstance(cell, EntityCellCustomField):
            return self._accept_cfield(cell.custom_field, not_hiddable_cell_keys)


class AggregatorConstraintsRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self) -> None:
        self._constraints_by_type_id: dict[str, type[AggregatorCellConstraint]] = {}

    def cell_constraints(self,
                         model: type[CremeEntity],
                         ) -> Iterator[AggregatorCellConstraint]:
        for constraint_class in self._constraints_by_type_id.values():
            yield constraint_class(model)

    def get_constraint_by_aggr_id(self,
                                  model: type[CremeEntity],
                                  aggr_id: str,
                                  ) -> AggregatorCellConstraint | None:
        for constraint_cls in self._constraints_by_type_id.values():
            if aggr_id in constraint_cls.aggregator_ids:
                return constraint_cls(model)

        return None

    def register_cell_constraints(
            self,
            *constraint_classes: type[AggregatorCellConstraint],
    ) -> AggregatorConstraintsRegistry:
        for constraint_cls in constraint_classes:
            if self._constraints_by_type_id.setdefault(
                    constraint_cls.type_id, constraint_cls,
            ) is not constraint_cls:
                raise self.RegistrationError(
                    f'{type(self).__name__}.register_cell_constraints(): '
                    f'a constraint with type_id="{constraint_cls.type_id}" is already registered.'
                )

        return self


ordinate_constraints = AggregatorConstraintsRegistry(
).register_cell_constraints(
    ACCCount,
    ACCFieldAggregation,
)
