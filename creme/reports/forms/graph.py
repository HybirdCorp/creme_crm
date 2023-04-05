################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from collections import defaultdict
from functools import partial
from json import dumps as json_dump

from django import forms
from django.forms.utils import ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellCustomField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.forms.base import CremeModelForm
from creme.creme_core.forms.fields import JSONField
from creme.creme_core.forms.widgets import (
    ChainedInput,
    DynamicInput,
    PolymorphicInput,
)
from creme.creme_core.models import CremeEntity
from creme.creme_core.models.fields import MoneyField
from creme.creme_core.utils.unicode_collation import collator

from .. import get_rgraph_model
from ..constants import AbscissaGroup, OrdinateAggregator
from ..core.graph import AbscissaInfo, OrdinateInfo
from ..core.graph.cell_constraint import (
    AggregatorCellConstraint,
    AggregatorConstraintsRegistry,
    GraphHandCellConstraint,
    GraphHandConstraintsRegistry,
)
from ..report_chart_registry import report_chart_registry


# Abscissa ---------------------------------------------------------------------
class AbscissaWidget(ChainedInput):
    cell_groups: list[type[EntityCell]] = [
        EntityCellRegularField,
        EntityCellRelation,
        EntityCellCustomField,
        # EntityCellFunctionField,
    ]

    cell_data_name = 'entity_cell'
    gtype_data_name = 'graph_type'
    cell_key_data_name = 'cell_key'
    gtype_id_data_name = 'type_id'
    constraint_data_name = 'grouping_category'
    parameter_data_name = 'parameter'

    def __init__(self,
                 attrs=None,
                 model=CremeEntity,
                 constraint_registry: GraphHandConstraintsRegistry | None = None,
                 ):
        super().__init__(attrs=attrs)
        self.model: type[CremeEntity] = model
        self.constraint_registry: GraphHandConstraintsRegistry = \
            constraint_registry or GraphHandConstraintsRegistry()
        self.not_hiddable_cell_keys: set[str] = set()

    def build_cell_choices(self):
        constraints_by_cell_cls = defaultdict(list)
        for constraint in self.constraint_registry.cell_constraints(self.model):
            constraints_by_cell_cls[constraint.cell_class].append(constraint)

        cells_by_cls = {}
        sort_key = collator.sort_key

        for cell_cls, constraints in constraints_by_cell_cls.items():
            cells = []
            for constraint in constraints:
                for cell in constraint.cells(self.not_hiddable_cell_keys):
                    cell.grouping_category = constraint.type_id  # NB: new dynamic attribute
                    cells.append(cell)

            cells.sort(key=lambda cell: sort_key(str(cell)))

            cells_by_cls[cell_cls] = cells

        cell_choices = []
        for cell_cls in self.cell_groups:
            cells = cells_by_cls.get(cell_cls)

            if cells:
                ckey_dname = self.cell_key_data_name
                constraint_dname = self.constraint_data_name

                cell_choices.append(
                    (
                        cell_cls.verbose_name,
                        [
                            (
                                json_dump({
                                    ckey_dname: cell.key,
                                    constraint_dname: cell.grouping_category,
                                }),
                                str(cell)
                            ) for cell in cells
                        ]
                    )
                )

        return cell_choices

    def build_graph_type_choices(self):
        registry = self.constraint_registry
        gtype_id_dname = self.gtype_id_data_name
        constraint_dname = self.constraint_data_name
        get_constraint = partial(registry.get_constraint_by_rgraph_type, model=self.model)

        return [
            (
                json_dump({
                    gtype_id_dname: rgraph_type,
                    constraint_dname: get_constraint(rgraph_type=rgraph_type).type_id,
                }),
                # GROUP_TYPES.get(rgraph_type, '??'),
                AbscissaGroup(rgraph_type).label,
            ) for rgraph_type in registry.rgraph_types
        ]

    def build_parameter_input(self):
        sub_attrs = {'auto': False}
        pinput = PolymorphicInput(
            key=f'${{{self.gtype_data_name}.{self.gtype_id_data_name}}}',
            attrs=sub_attrs,
        )

        pinput.set_default_input(widget=DynamicInput, attrs=sub_attrs, type='hidden')

        for gtype_id, validator in self.constraint_registry.parameter_validators:
            if validator:
                pinput.add_input(
                    str(gtype_id),
                    widget=DynamicInput,
                    attrs={
                        **sub_attrs,
                        'placeholder': validator.label,
                        'title': validator.label,
                    },
                    type=validator.widget.input_type,
                )

        return pinput

    def get_context(self, name, value, attrs):
        field_attrs = {'auto': False, 'datatype': 'json'}
        cell_data_name = self.cell_data_name
        constraint_dname = self.constraint_data_name

        self.add_dselect(
            cell_data_name,
            options=self.build_cell_choices(),
            attrs={
                **field_attrs,
                'autocomplete': True,
            },
            avoid_empty=True,
        )
        self.add_dselect(
            self.gtype_data_name,
            options=self.build_graph_type_choices(),
            attrs={
                **field_attrs,
                'filter': (
                    f'context.{cell_data_name} && item.value ? '
                    f'item.value.{constraint_dname} ==='
                    f' context.{cell_data_name}.{constraint_dname} : '
                    f'true'
                ),
                'dependencies': cell_data_name,
            },
            avoid_empty=True,
        )
        self.add_input(
            self.parameter_data_name,
            self.build_parameter_input(),
            attrs=field_attrs,
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class AbscissaField(JSONField):
    default_error_messages = {
        'ecellrequired':   'The entity cell is required.',
        'ecellnotallowed': 'This entity cell is not allowed.',

        'graphtyperequired':   'The graph type is required.',
        'graphtypenotallowed': 'The graph type is not allowed.',

        'invalidparameter': _('The parameter is invalid. {}'),
    }

    value_type = dict
    widget = AbscissaWidget

    cell_data_name       = AbscissaWidget.cell_data_name
    gtype_data_name      = AbscissaWidget.gtype_data_name
    cell_key_data_name   = AbscissaWidget.cell_key_data_name
    gtype_id_data_name   = AbscissaWidget.gtype_id_data_name
    constraint_data_name = AbscissaWidget.constraint_data_name
    parameter_data_name  = AbscissaWidget.parameter_data_name

    _model: type[CremeEntity]
    _constraint_registry: GraphHandConstraintsRegistry
    not_hiddable_cell_keys: set[str]

    def __init__(self, *, model=CremeEntity, abscissa_constraints=None, **kwargs):
        self._initial = None
        super().__init__(**kwargs)
        self.model = model
        self.constraint_registry = abscissa_constraints or GraphHandConstraintsRegistry()
        # TODO: when required=False => empty choice for cell/graph type

    @property
    def constraint_registry(self):
        return self._constraint_registry

    @constraint_registry.setter
    def constraint_registry(self, registry: GraphHandConstraintsRegistry):
        self._constraint_registry = self.widget.constraint_registry = registry

    @property
    def initial(self):
        return self._initial

    @initial.setter
    def initial(self, value):
        self._initial = value
        if value is None:
            not_hiddable_cell_keys = set()
        else:
            assert isinstance(value, AbscissaInfo), type(value)
            # NB: If a cell (for a regular-field) has been selected before the
            #     related regular field has been hidden, it must be proposed to
            #     avoid silent modification of the abscissa (& so, the ReportGraph).
            not_hiddable_cell_keys = {value.cell.key}

        # TODO: property "not_hiddable_cell_keys" in widget to copy ??
        self.not_hiddable_cell_keys = self.widget.not_hiddable_cell_keys = not_hiddable_cell_keys

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = self.widget.model = model

    def _clean_cell(self, data, constraint: GraphHandCellConstraint) -> EntityCell | None:
        clean_value = self.clean_value
        required = self.required

        cell_info = clean_value(
            data, self.cell_data_name, dict, required, 'ecellrequired',
        )
        if not cell_info:
            raise ValidationError(
                self.error_messages['ecellrequired'], code='ecellrequired',
            )

        cell_key = clean_value(
            cell_info, self.cell_key_data_name, str, required, 'ecellrequired',
        )

        if not cell_key:
            return None

        cell = constraint.get_cell(
            cell_key=cell_key,
            not_hiddable_cell_keys=self.not_hiddable_cell_keys,
        )
        if cell is None:
            raise ValidationError(
                self.error_messages['ecellnotallowed'], code='ecellnotallowed',
            )

        return cell

    def _clean_graph_type(self, data) -> int | None:
        clean_value = self.clean_value
        required = self.required

        gtype_info = clean_value(data, self.gtype_data_name, dict, required, 'graphtyperequired')
        if not gtype_info:
            raise ValidationError(
                self.error_messages['graphtyperequired'],
                code='graphtyperequired',
            )

        return clean_value(gtype_info, self.gtype_id_data_name, int, required, 'graphtyperequired')

    def _clean_parameter(self, data, graph_type: int):
        validator = self.constraint_registry.get_parameter_validator(graph_type)

        if validator:
            value = data.get('parameter')

            try:
                parameter = validator.clean(value)
            except ValidationError as e:
                raise ValidationError(
                    self.error_messages['invalidparameter'].format(e.message),
                    code='invalidparameter',
                ) from e
        else:
            # TODO: validate data is empty
            parameter = None

        return parameter

    def _value_from_unjsonfied(self, data):
        gtype = self._clean_graph_type(data)
        if gtype is None:
            return None

        constraint = self.constraint_registry.get_constraint_by_rgraph_type(
            model=self.model,
            rgraph_type=gtype,
        )
        if constraint is None:
            raise ValidationError(
                self.error_messages['graphtypenotallowed'],
                code='graphtypenotallowed',
            )

        cell = self._clean_cell(data, constraint=constraint)
        if not cell:
            return None

        return AbscissaInfo(
            cell=cell,
            graph_type=gtype,
            parameter=self._clean_parameter(data, graph_type=gtype),
        )

    def _value_to_jsonifiable(self, value):
        constraint = self.constraint_registry.get_constraint_by_rgraph_type(
            model=self.model,
            rgraph_type=value.graph_type,
        )
        category = constraint.type_id if constraint else '??'
        constraint_dname = self.constraint_data_name

        return {
            self.cell_data_name: {
                self.cell_key_data_name: value.cell.key,
                constraint_dname: category,
            },
            self.gtype_data_name: {
                self.gtype_id_data_name: value.graph_type,
                constraint_dname: category,
            },
            self.parameter_data_name: value.parameter or '',
        }


# Ordinate ---------------------------------------------------------------------
class OrdinateWidget(ChainedInput):
    cell_groups: list[type[EntityCell]] = [
        EntityCellRegularField,
        EntityCellRelation,
        EntityCellCustomField,
        # EntityCellFunctionField,
    ]

    cell_data_name = 'entity_cell'
    aggr_data_name = 'aggregator'

    cell_key_data_name = 'cell_key'
    aggr_id_data_name = 'aggr_id'
    constraint_data_name = 'aggr_category'

    def __init__(self,
                 attrs=None,
                 model=CremeEntity,
                 constraint_registry: AggregatorConstraintsRegistry | None = None,
                 ):
        super().__init__(attrs=attrs)
        self.model: type[CremeEntity] = model
        self.constraint_registry: AggregatorConstraintsRegistry = (
            constraint_registry or AggregatorConstraintsRegistry()
        )
        self.not_hiddable_cell_keys: set[str] = set()

    def build_aggr_choices(self, cells_per_aggr_category):
        aggr_choices = []
        aggr_id_dname = self.aggr_id_data_name
        constraint_dname = self.constraint_data_name

        # TODO: sort ?
        for cell_constraint in self.constraint_registry.cell_constraints(self.model):
            category = cell_constraint.type_id

            if not cell_constraint.cell_classes or cells_per_aggr_category.get(category):
                for aggr_id in cell_constraint.aggregator_ids:
                    aggr_choices.append(
                        (
                            json_dump({
                                aggr_id_dname: aggr_id,
                                constraint_dname: category,
                            }),
                            OrdinateAggregator(aggr_id).label,
                        )
                    )

        return aggr_choices

    def build_cell_choices(self, cells_per_aggr_category):
        cells_by_cls = defaultdict(list)
        sort_key = collator.sort_key

        for category, cells in cells_per_aggr_category.items():
            for cell in cells:
                cell.grouping_category = category  # NB: new dynamic attribute
                cells_by_cls[type(cell)].append(cell)

        ckey_dname = self.cell_key_data_name
        constraint_dname = self.constraint_data_name
        cell_choices = []
        for cell_cls in self.cell_groups:
            cells = cells_by_cls.get(cell_cls)

            if cells:
                cells.sort(key=lambda cell: sort_key(str(cell)))

                cell_choices.append(
                    (
                        cell_cls.verbose_name,
                        [
                            (
                                json_dump({
                                    ckey_dname: cell.key,
                                    constraint_dname: cell.grouping_category,
                                }),
                                str(cell)
                            ) for cell in cells
                        ]
                    )
                )

        return cell_choices

    def get_context(self, name, value, attrs):
        # We build the cells once to avoid some queries (to retrieve CustomFields)
        cells_per_aggr_category = defaultdict(list)
        for cell_constraint in self.constraint_registry.cell_constraints(self.model):
            cells_per_aggr_category[cell_constraint.type_id].extend(
                cell_constraint.cells(self.not_hiddable_cell_keys)
            )

        field_attrs = {'auto': False, 'datatype': 'json'}
        aggr_data_name = self.aggr_data_name
        constraint_dname = self.constraint_data_name

        self.add_dselect(
            aggr_data_name,
            options=self.build_aggr_choices(cells_per_aggr_category),
            attrs=field_attrs,
            avoid_empty=True,
        )
        self.add_dselect(
            self.cell_data_name,
            options=self.build_cell_choices(cells_per_aggr_category),
            attrs={
                **field_attrs,
                'filter': (
                    f'context.{aggr_data_name} && item.value ? '
                    f'item.value.{constraint_dname} ==='
                    f' context.{aggr_data_name}.{constraint_dname} : '
                    f'true'
                ),
                'dependencies': aggr_data_name,
            },
        )

        return super().get_context(name=name, value=value, attrs=attrs)


class OrdinateField(JSONField):
    default_error_messages = {
        'aggridrequired': 'The aggregation id is required.',
        'aggridinvalid':  'The aggregation id is invalid.',

        'ecellrequired':   'The entity cell is required.',
        'ecellnotallowed': 'This entity cell is not allowed.',
    }

    value_type = dict
    widget = OrdinateWidget

    aggr_data_name       = OrdinateWidget.aggr_data_name
    aggr_id_data_name    = OrdinateWidget.aggr_id_data_name
    cell_data_name       = OrdinateWidget.cell_data_name
    cell_key_data_name   = OrdinateWidget.cell_key_data_name
    constraint_data_name = OrdinateWidget.constraint_data_name

    _model: type[CremeEntity]
    _constraint_registry: AggregatorConstraintsRegistry
    not_hiddable_cell_keys: set[str]

    def __init__(self, *,
                 model=CremeEntity,
                 ordinate_constraints=None,
                 **kwargs):
        self._initial = None
        super().__init__(**kwargs)
        self.model = model
        self.constraint_registry = ordinate_constraints or AggregatorConstraintsRegistry()
        # TODO: when required=False => empty choice for aggr type

    @property
    def constraint_registry(self):
        return self._constraint_registry

    @constraint_registry.setter
    def constraint_registry(self, registry: AggregatorConstraintsRegistry):
        self._constraint_registry = self.widget.constraint_registry = registry

    @property
    def initial(self):
        return self._initial

    @initial.setter
    def initial(self, value):
        self._initial = value
        if value is None:
            not_hiddable_cell_keys = set()
        else:
            assert isinstance(value, OrdinateInfo), type(value)
            # NB: If a cell (for a regular-field) has been selected before the
            #     related regular field has been hidden, it must be proposed to
            #     avoid silent modification of the ordinate (& so, the ReportGraph).
            cell = value.cell
            not_hiddable_cell_keys = {value.cell.key} if cell else set()

        # TODO: property "not_hiddable_cell_keys" in widget to copy ??
        self.not_hiddable_cell_keys = self.widget.not_hiddable_cell_keys = not_hiddable_cell_keys

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = self.widget.model = model

    def _clean_aggr_id(self, data) -> str | None:
        clean_value = self.clean_value

        aggr_info = clean_value(data, self.aggr_data_name, dict, True, 'aggridrequired')
        if not aggr_info:
            raise ValidationError(
                self.error_messages['aggridrequired'],
                code='aggridrequired',
            )

        return clean_value(
            aggr_info, self.aggr_id_data_name, str, self.required, 'aggridrequired',
        )

    def _clean_cell(self,
                    data, constraint: AggregatorCellConstraint,
                    ) -> EntityCell | None:
        clean_value = self.clean_value

        cell_info = clean_value(data, self.cell_data_name, dict, False, 'ecellrequired')
        if not cell_info:
            if constraint.cell_classes:
                raise ValidationError(
                    self.error_messages['ecellrequired'],
                    code='ecellrequired',
                )

            return None

        cell_key = clean_value(cell_info, self.cell_key_data_name, str, True, 'ecellrequired')
        if not cell_key:
            raise ValidationError(
                self.error_messages['ecellrequired'],
                code='ecellrequired',
            )

        cell = constraint.get_cell(
            cell_key=cell_key,
            not_hiddable_cell_keys=self.not_hiddable_cell_keys,
        )
        if cell is None:
            raise ValidationError(
                self.error_messages['ecellnotallowed'],
                code='ecellnotallowed',
            )

        return cell

    def _value_from_unjsonfied(self, data):
        aggr_id = self._clean_aggr_id(data)
        if not aggr_id:
            return None

        constraint = self.constraint_registry.get_constraint_by_aggr_id(
            model=self.model,
            aggr_id=aggr_id,
        )
        if constraint is None:
            raise ValidationError(
                self.error_messages['aggridinvalid'],
                code='aggridinvalid',
            )

        cell = self._clean_cell(data, constraint)

        return OrdinateInfo(
            aggr_id=aggr_id,
            cell=cell,
        )

    def _value_to_jsonifiable(self, value):
        cell = value.cell

        constraint = self.constraint_registry.get_constraint_by_aggr_id(
            model=self.model,
            aggr_id=value.aggr_id,
        )
        category = constraint.type_id if constraint else '??'
        constraint_dname = self.constraint_data_name

        return {
            self.aggr_data_name: {
                self.aggr_id_data_name: value.aggr_id,
                constraint_dname: category,
            },
            self.cell_data_name: {
                self.cell_key_data_name: cell.key,
                constraint_dname: category,
            } if cell else None,
        }


# ------------------------------------------------------------------------------
# NB: not <CremeEntityForm> to avoid Relationships & CremeProperties
class ReportGraphForm(CremeModelForm):
    chart = forms.ChoiceField(label=_('Chart type'), choices=report_chart_registry.choices())
    abscissa = AbscissaField(label=_('X axis'))
    ordinate = OrdinateField(label=_('Y axis'))

    blocks = CremeModelForm.blocks.new(
        {'id': 'abscissa', 'label': _('X axis'), 'fields': ['abscissa']},
        {'id': 'ordinate', 'label': _('Y axis'), 'fields': ['ordinate']},
    )

    class Meta(CremeModelForm.Meta):
        model = get_rgraph_model()
        exclude = ('description',)

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report = entity
        report_ct = entity.ct
        model = report_ct.model_class()

        instance = self.instance
        fields = self.fields

        # Abscissa -------------------------------------------------------------
        abscissa_f = fields['abscissa']
        abscissa_f.model = model
        abscissa_f.constraint_registry = instance.abscissa_constraints

        # Ordinate -------------------------------------------------------------
        ordinate_f = fields['ordinate']
        ordinate_f.model = model
        ordinate_f.constraint_registry = instance.ordinate_constraints

        # TODO: sadly it performs a query to get the CustomFields => cache
        money_fields = [
            cell.field_info[-1]
            for cell_constraint in instance.ordinate_constraints.cell_constraints(model)
            for cell in cell_constraint.cells(ordinate_f.not_hiddable_cell_keys)
            if (
                isinstance(cell, EntityCellRegularField)
                and isinstance(cell.field_info[-1], MoneyField)
            )
        ]
        if money_fields:
            ordinate_f.help_text = gettext(
                'If you use a field related to money, the entities should use the same '
                'currency or the result will be wrong. Concerned fields are : {}'
            ).format(', '.join(str(field.verbose_name) for field in money_fields))

        # Initial data ---------------------------------------------------------
        if instance.pk:
            abscissa_f.initial = instance.abscissa_info
            ordinate_f.initial = instance.ordinate_info

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        graph = self.instance
        graph.linked_report = self.report
        graph.abscissa_info = cdata['abscissa']
        graph.ordinate_info = cdata['ordinate']

        return super().save(*args, **kwargs)
