# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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
from json import dumps as json_dump
from functools import partial
from typing import (
    Any,  Optional, Type,
    Container, Iterable, Iterator,
    Dict, Set, Tuple,
)

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey  # FieldDoesNotExist, DateTimeField, DateField
# from django.db.models.fields.related import RelatedField
from django.forms.utils import ValidationError
# from django.urls import reverse
from django.utils.translation import gettext_lazy as _, gettext

from creme.creme_core.core.entity_cell import (
    EntityCell,
    EntityCellRegularField,
    EntityCellCustomField,
    EntityCellRelation,
)
from creme.creme_core.forms.base import CremeModelForm
from creme.creme_core.forms.fields import JSONField  # AjaxChoiceField
from creme.creme_core.forms.widgets import (
    # DependentSelect,
    ChainedInput,
    PolymorphicInput,
    DynamicInput,
)
from creme.creme_core.models import CremeEntity, RelationType, CustomField, FieldsConfig
from creme.creme_core.models.fields import MoneyField
from creme.creme_core.utils.meta import ModelFieldEnumerator, is_date_field
from creme.creme_core.utils.unicode_collation import collator

from .. import get_rgraph_model
from ..constants import (
    GROUP_TYPES,
    RGT_DAY, RGT_MONTH, RGT_YEAR, RGT_RANGE,
    RGT_FK, RGT_RELATION,
    RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR, RGT_CUSTOM_RANGE,
    RGT_CUSTOM_FK,
)
# from ..core.graph import RGRAPH_HANDS_MAP
from ..report_aggregation_registry import field_aggregation_registry
from ..report_chart_registry import report_chart_registry


# class AbscissaGroupBySelect(forms.Select):
#     def get_context(self, name, value, attrs):
#         extra_args = {
#             'onchange': "creme.reports.toggleDaysField($(this), [{}]);".format(
#                             ','.join(f"'{t}'" for t in (RGT_CUSTOM_RANGE, RGT_RANGE))
#                         ),
#         }
#         if attrs is not None:
#             extra_args.update(attrs)
#
#         return super().get_context(name=name, value=value, attrs=extra_args)

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


# TODO: move to reports/core/graph ??
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
    rgraph_types=[RGT_FK],
).register_cell_constraint(
    constraint_class=GHCCRegularDate,
    rgraph_types=[
        RGT_DAY,
        RGT_MONTH,
        RGT_YEAR,
        RGT_RANGE,
    ],
).register_cell_constraint(
    constraint_class=GHCCRelation,
    rgraph_types=[RGT_RELATION],
).register_cell_constraint(
    constraint_class=GHCCCustomEnum,
    rgraph_types=[RGT_CUSTOM_FK],
).register_cell_constraint(
    constraint_class=GHCCCustomDate,
    rgraph_types=[
        RGT_CUSTOM_DAY,
        RGT_CUSTOM_MONTH,
        RGT_CUSTOM_YEAR,
        RGT_CUSTOM_RANGE,
    ],
).register_parameter_validator(
    rgraph_types=[RGT_RANGE, RGT_CUSTOM_RANGE],
    formfield=forms.IntegerField(label=_('Number of days')),
)


class AbscissaInfo:
    def __init__(self,
                 cell: EntityCell,
                 graph_type: int,
                 parameter: Optional[Any] = None):
        self.cell = cell
        self.graph_type = graph_type
        self.parameter = parameter

    def __repr__(self):
        return f'AbscissaInfo(cell=<{self.cell}>, ' \
                            f'graph_type={self.graph_type}, ' \
                            f'parameter={self.parameter})'


class AbscissaWidget(ChainedInput):
    cell_groups = [
        (EntityCellRegularField, _('Fields')),
        (EntityCellRelation,     _('Relationships')),
        (EntityCellCustomField,  _('Custom fields')),
        # (EntityCellFunctionField, _('Function fields')),
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
                 constraint_registry: Optional[GraphHandConstraintsRegistry] = None):
        super().__init__(attrs=attrs)
        self.model: Type[CremeEntity] = model
        self.constraint_registry: GraphHandConstraintsRegistry = \
            constraint_registry or GraphHandConstraintsRegistry()
        self.not_hiddable_cell_keys: Set[int] = set()

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
        for cell_cls, group_title in self.cell_groups:
            cells = cells_by_cls.get(cell_cls)

            if cells:
                ckey_dname = self.cell_key_data_name
                constraint_dname = self.constraint_data_name

                cell_choices.append(
                    (group_title,
                     [(json_dump({
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
            (json_dump({
                gtype_id_dname: rgraph_type,
                constraint_dname: get_constraint(rgraph_type=rgraph_type).type_id,
             }),
             GROUP_TYPES.get(rgraph_type, '??'),
            ) for rgraph_type in registry.rgraph_types
        ]

    def build_parameter_input(self):
        sub_attrs = {'auto': False}
        pinput = PolymorphicInput(
            key='${%s.%s}' % (self.gtype_data_name, self.gtype_id_data_name),
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
        )
        self.add_dselect(
            self.gtype_data_name,
            options=self.build_graph_type_choices(),
            attrs={
                **field_attrs,
                'filter': f'context.{cell_data_name} && item.value ? '
                          f'item.value.{constraint_dname} === context.{cell_data_name}.{constraint_dname} : '
                          f'true',
                'dependencies': cell_data_name,
            },
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

    _model: Type[CremeEntity]
    _constraint_registry: GraphHandConstraintsRegistry
    not_hiddable_cell_keys: Set[str]

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
            assert isinstance(value, AbscissaInfo)
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

    def _clean_cell(self, data, constraint: GraphHandCellConstraint) -> Optional[EntityCell]:
        clean_value = self.clean_value
        required = self.required

        cell_info = clean_value(data, self.cell_data_name, dict, required, 'ecellrequired')
        if not cell_info:
            raise ValidationError(self.error_messages['ecellrequired'],
                                  code='ecellrequired',
                                 )

        cell_key = clean_value(cell_info, self.cell_key_data_name, str, required, 'ecellrequired')

        if not cell_key:
            return None

        cell = constraint.get_cell(
            cell_key=cell_key,
            not_hiddable_cell_keys=self.not_hiddable_cell_keys,
        )
        if cell is None:
            raise ValidationError(self.error_messages['ecellnotallowed'],
                                  code='ecellnotallowed',
                                 )

        return cell

    def _clean_graph_type(self, data) -> Optional[int]:
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


class ReportGraphForm(CremeModelForm):  # NB: not <CremeEntityForm> to avoid Relationships & CremeProperties
    chart = forms.ChoiceField(label=_('Chart type'), choices=report_chart_registry.choices())

    # abscissa_field = forms.ChoiceField(
    #     label=_('Field'), choices=(),
    #     widget=DependentSelect(target_id='id_abscissa_group_by'),
    # )
    # abscissa_group_by = AjaxChoiceField(
    #     label=_('Grouping'), choices=(),
    #     widget=AbscissaGroupBySelect(attrs={'id': 'id_abscissa_group_by'}),
    # )
    abscissa = AbscissaField(label=_('X axis'))

    aggregate = forms.ChoiceField(
        label=_('Aggregate'), required=False,
        choices=[(agg.name, agg.title)
                    for agg in field_aggregation_registry.aggregations
                ],
    )
    aggregate_field = forms.ChoiceField(label=_('Field'), choices=(), required=False)
    is_count        = forms.BooleanField(
        label=_('Entities count'), required=False,
        help_text=_('Make a count instead of aggregate ?'),
        widget=forms.CheckboxInput(
             attrs={'onchange': "creme.reports.toggleDisableOthers(this, ['#id_aggregate', '#id_aggregate_field']);"},
        ),
    )

    blocks = CremeModelForm.blocks.new(
        # ('abscissa', _('X axis'), ['abscissa_field', 'abscissa_group_by', 'days']),
        ('abscissa', _('X axis'), ['abscissa']),
        ('ordinate', _('Y axis'), ['is_count', 'aggregate', 'aggregate_field']),
    )

    abscissa_constraints = abscissa_constraints

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

        # abscissa_field_f  = fields['abscissa_field']
        abscissa_f = fields['abscissa']
        aggregate_field_f = fields['aggregate_field']
        is_count_f        = fields['is_count']

        get_fconf = FieldsConfig.LocalCache().get_4_model
        # TODO: split('__', 1) when 'count' is an aggregate operator
        ordinate_field_name, __, aggregate = instance.ordinate.rpartition('__')

        # Abscissa -------------------------------------------------------------
        # def absc_field_excluder(field, deep):
        #     if isinstance(field, RelatedField) and \
        #        issubclass(field.remote_field.model, CremeEntity):
        #         return True
        #
        #     return get_fconf(field.model).is_field_hidden(field) and \
        #            field.name != instance.abscissa
        #
        # abscissa_model_fields = ModelFieldEnumerator(model, deep=0, only_leafs=False) \
        #                             .filter(self._filter_abcissa_field, viewable=True) \
        #                             .exclude(absc_field_excluder) \
        #                             .choices()
        #
        # self.rtypes = rtypes = dict(RelationType.objects
        #                                         .compatible(report_ct, include_internals=True)
        #                                         .values_list('id', 'predicate')
        #                            )
        # abscissa_predicates = [*rtypes.items()]
        # sort_key = collator.sort_key
        # abscissa_predicates.sort(key=lambda k: sort_key(k[1]))
        #
        # abscissa_choices = [
        #     (_('Fields'),        abscissa_model_fields),
        #     (_('Relationships'), abscissa_predicates),
        # ]
        #
        # self.abs_cfields = cfields = {
        #     cf.id: cf
        #         for cf in CustomField.objects
        #                              .filter(field_type__in=(CustomField.ENUM,
        #                                                      CustomField.DATETIME,
        #                                                     ),
        #                                      content_type=report_ct,
        #                                     )
        # }
        #
        # if cfields:
        #     abscissa_choices.append(
        #         (_('Custom fields'), [(cf.id, cf.name) for cf in cfields.values()])
        #     )
        #
        # abscissa_field_f.choices = abscissa_choices
        # abscissa_field_f.widget.target_url = reverse('reports__graph_types', args=(report_ct.id,))

        abscissa_f.model = model
        abscissa_f.constraint_registry = self.abscissa_constraints

        # Ordinate -------------------------------------------------------------
        def agg_field_excluder(field, deep):
            return get_fconf(field.model).is_field_hidden(field) and \
                   field.name != ordinate_field_name

        aggfields = [
            field_info[0]
                for field_info in ModelFieldEnumerator(model, deep=0)
                                    .filter((lambda f, depth: isinstance(f, field_aggregation_registry.authorized_fields)),
                                            viewable=True
                                           )
                                    .exclude(agg_field_excluder)
        ]
        aggfield_choices = [(field.name, field.verbose_name) for field in aggfields]
        aggcustom_choices = [
            *CustomField.objects
                        .filter(field_type__in=field_aggregation_registry.authorized_customfields,
                                content_type=report_ct,
                               )
                        .values_list('id', 'name')
        ]
        ordinate_choices = aggfield_choices or aggcustom_choices

        if ordinate_choices:
            self.force_count = False

            money_fields = [field for field in aggfields if isinstance(field, MoneyField)]
            if money_fields:
                # TODO: lazy lazily-translated-string interpolation
                aggregate_field_f.help_text = gettext(
                        'If you use a field related to money, the entities should use the same '
                        'currency or the result will be wrong. Concerned fields are : {}'
                    ).format(', '.join(str(field.verbose_name) for field in money_fields))

            if aggcustom_choices and aggfield_choices:
                ordinate_choices = [
                    (_('Fields'),        aggfield_choices),
                    (_('Custom fields'), aggcustom_choices),
                ]
        else:
            self.force_count = True
            ordinate_choices = [('', _('No field is usable for aggregation'))]

            disabled_attrs = {'disabled': True}
            aggregate_field_f.widget.attrs = disabled_attrs
            fields['aggregate'].widget.attrs = disabled_attrs

            is_count_f.help_text = _('You must make a count because no field is usable for aggregation')
            is_count_f.initial = True
            is_count_f.widget.attrs = disabled_attrs

        aggregate_field_f.choices = ordinate_choices

        # Initial data ---------------------------------------------------------
        data = self.data

        # if data:
        #     get_data = data.get
        #     widget = abscissa_field_f.widget
        #     widget.source_val = get_data('abscissa_field')
        #     widget.target_val = get_data('abscissa_group_by')
        #
        #     fields['abscissa_group_by'].widget.attrs['data-initial-value'] = get_data('abscissa_group_by')
        # elif instance.pk is not None:
        if instance.pk:
            fields['aggregate'].initial = aggregate
            aggregate_field_f.initial   = ordinate_field_name
            # abscissa_field_f.initial    = instance.abscissa
            #
            # widget = abscissa_field_f.widget
            # widget.source_val = instance.abscissa
            # widget.target_val = instance.type
            #
            # fields['abscissa_group_by'].widget.attrs['data-initial-value'] = instance.type
            abscissa_constraint = self.abscissa_constraints.get_constraint_by_rgraph_type(
                model=model,
                rgraph_type=instance.type,
            )
            if abscissa_constraints:  # TODO: log if None ?
                abscissa_f.initial = AbscissaInfo(
                    cell=abscissa_constraint.cell_class.build(
                        model,
                        instance.abscissa,
                    ),
                    graph_type=instance.type,
                    parameter=instance.days,
                )

        # TODO: remove this sh*t when is_count is a real widget well initialized (disabling set by JS)
        if is_count_f.initial or instance.is_count or data.get('is_count'):
            disabled_attrs = {'disabled': True}
            aggregate_field_f.widget.attrs = disabled_attrs
            fields['aggregate'].widget.attrs = disabled_attrs

    # def _filter_abcissa_field(self, field, depth):
    #     if isinstance(field, DateField):
    #         return True
    #
    #     if isinstance(field, ForeignKey):
    #         return field.get_tag('enumerable')
    #
    #     return False

    # def clean_abscissa_group_by(self):
    #     str_val = self.cleaned_data.get('abscissa_group_by')
    #
    #     if not str_val:
    #         raise ValidationError(self.fields['abscissa_group_by'].error_messages['required'])
    #
    #     try:
    #         graph_type = int(str_val)
    #     except Exception as e:
    #         raise ValidationError('Invalid value: {}  [{}]'.format(str_val, e)) from e
    #
    #     hand = RGRAPH_HANDS_MAP.get(graph_type)
    #
    #     if hand is None:
    #         raise ValidationError(
    #             'Invalid value: {} not in {}'.format(
    #                 graph_type,
    #                 [h.hand_id for h in RGRAPH_HANDS_MAP],
    #         ))
    #
    #     self.verbose_graph_type = hand.verbose_name
    #
    #     return graph_type

    def clean_is_count(self):
        return self.cleaned_data.get('is_count', False) or self.force_count

    # def _clean_field(self, model, name, field_types, formfield_name='abscissa_field'):
    #     try:
    #         field = model._meta.get_field(name)
    #     except FieldDoesNotExist:
    #         self.add_error(
    #             formfield_name,
    #             f'If you choose to group "{self.verbose_graph_type}" you have to choose a field.'
    #         )
    #     else:
    #         if not isinstance(field, field_types):
    #             self.add_error(
    #                 formfield_name,
    #                 '"{}" groups are only compatible with [{}]'.format(
    #                      self.verbose_graph_type,
    #                      ', '.join(ftype.__name__ for ftype in field_types),
    #                 )
    #             )
    #         else:
    #             return field

    # def _clean_customfield(self, name, cfield_types, formfield_name='abscissa_field'):
    #     if not name or not name.isdigit():
    #         self.add_error(formfield_name, 'Unknown or invalid custom field.')
    #     else:
    #         cfield = self.abs_cfields[int(name)]
    #
    #         if cfield.field_type not in cfield_types:
    #             self.add_error(
    #                 formfield_name,
    #                 '"{}" groups are only compatible with [{}]'.format(
    #                      self.verbose_graph_type,
    #                      ', '.join(map(str, cfield_types)),
    #                 )
    #             )
    #         else:
    #             return cfield

    def clean(self):
        cleaned_data = super().clean()
        get_data     = cleaned_data.get
        # model = self.report.ct.model_class()
        #
        # abscissa_name = get_data('abscissa_field')
        # abscissa_group_by = cleaned_data['abscissa_group_by']
        #
        # if abscissa_group_by == RGT_FK:
        #     self._clean_field(model, abscissa_name, field_types=(ForeignKey,))
        # elif abscissa_group_by == RGT_CUSTOM_FK:
        #     self._clean_customfield(abscissa_name, cfield_types=(CustomField.ENUM,))
        # elif abscissa_group_by == RGT_RELATION:
        #     if abscissa_name not in self.rtypes:
        #         self.add_error('abscissa_field', 'Unknown relationship type.')
        # elif abscissa_group_by in (RGT_DAY, RGT_MONTH, RGT_YEAR):
        #     self._clean_field(model, abscissa_name, field_types=(DateField, DateTimeField))
        # elif abscissa_group_by == RGT_RANGE:
        #     self._clean_field(model, abscissa_name, field_types=(DateField, DateTimeField))
        #
        #     if not cleaned_data.get('days'):
        #         self.add_error(
        #             'days',
        #             _("You have to specify a day range if you use 'by X days'"),
        #         )
        # elif abscissa_group_by in (RGT_CUSTOM_DAY, RGT_CUSTOM_MONTH, RGT_CUSTOM_YEAR):
        #     self._clean_customfield(abscissa_name, cfield_types=(CustomField.DATETIME,))
        # elif abscissa_group_by == RGT_CUSTOM_RANGE:
        #     self._clean_customfield(abscissa_name, cfield_types=(CustomField.DATETIME,))
        #
        #     if not cleaned_data.get('days'):
        #         self.add_error(
        #             'days',
        #             _("You have to specify a day range if you use 'by X days'"),
        #         )
        # else:
        #     raise ValidationError('Unknown graph type')
        #
        # if cleaned_data.get('days') and abscissa_group_by not in (RGT_RANGE, RGT_CUSTOM_RANGE):
        #     cleaned_data['days'] = None

        if get_data('aggregate_field'):
            if not field_aggregation_registry.get(get_data('aggregate')):
                self.add_error(
                    'aggregate',
                    _('This field is required if you choose a field to aggregate.'),
                )
        elif not get_data('is_count'):
            raise ValidationError(
                gettext("If you don't choose an ordinate field (or none available) "
                        "you have to check 'Make a count instead of aggregate ?'"
                       )
            )

        return cleaned_data

    def save(self, *args, **kwargs):
        cdata = self.cleaned_data
        get_data = cdata.get
        graph = self.instance
        graph.linked_report = self.report

        # graph.abscissa = get_data('abscissa_field')
        # graph.type = get_data('abscissa_group_by')
        abs_info: AbscissaInfo = cdata['abscissa']
        graph.abscissa = abs_info.cell.value
        graph.type = abs_info.graph_type
        graph.days = abs_info.parameter

        agg_fields = get_data('aggregate_field')
        graph.ordinate = '{}__{}'.format(agg_fields, get_data('aggregate')) if agg_fields else ''

        return super().save(*args, **kwargs)
