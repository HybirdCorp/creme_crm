# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

import logging
# import warnings
from copy import deepcopy
# from functools import partial
from itertools import chain
from typing import Optional, Type

from django import forms
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.backends import export_backend_registry
from creme.creme_core.core import entity_cell
from creme.creme_core.forms import CremeForm  # CremeEntityForm
from creme.creme_core.forms import fields as core_fields
from creme.creme_core.forms import header_filter as hf_form
from creme.creme_core.gui.custom_form import CustomFormExtraSubCell
from creme.creme_core.models import (  # EntityFilter
    CremeEntity,
    CustomField,
    FieldsConfig,
    HeaderFilter,
)
from creme.creme_core.utils.meta import ModelFieldEnumerator, is_date_field

from .. import constants, get_report_model
from ..core.report import RHRelated
from ..models import Field
from ..report_aggregation_registry import field_aggregation_registry

logger = logging.getLogger(__name__)
Report = get_report_model()
reports_cells_registry = deepcopy(entity_cell.CELLS_MAP)


class FilteredCTypeSubCell(CustomFormExtraSubCell):
    sub_type_id = 'reports_filtered_ctype'
    verbose_name = _('Entity type & filter')

    def formfield(self, instance, user, **kwargs):
        return core_fields.FilteredEntityTypeField(label=self.verbose_name, user=user)

    def post_clean_instance(self, *, instance, value, form):
        if value:
            instance.ct, instance.filter = value


class FilterSubCell(CustomFormExtraSubCell):
    sub_type_id = 'reports_filter'
    verbose_name = _('Filter')

    filter_field_name = 'filter'
    ctype_field_name = 'ct'

    not_editable_flag = 'NOT EDITABLE'

    def formfield(self, instance, user, **kwargs):
        field_name = self.filter_field_name
        efilter = getattr(instance, field_name)

        if efilter and not efilter.can_view(user)[0]:
            return core_fields.ReadonlyMessageField(
                label=self.verbose_name,
                initial=_('The filter cannot be changed because it is private.'),
                return_value=self.not_editable_flag,
            )

        mfield = type(instance)._meta.get_field(field_name)

        choice_field = mfield.formfield()
        choice_field.empty_label = pgettext_lazy('creme_core-filter', 'All')
        choice_field.queryset = choice_field.queryset.filter(
            entity_type=getattr(instance, self.ctype_field_name),
        )
        choice_field.initial = efilter

        if hasattr(choice_field, 'get_limit_choices_to'):
            q_filter = choice_field.get_limit_choices_to()

            if q_filter is not None:
                choice_field.queryset = choice_field.queryset.complex_filter(q_filter)

        return choice_field

    def post_clean_instance(self, *, instance, value, form):
        if value != self.not_editable_flag:
            setattr(instance, self.filter_field_name, value)


class _ReportOnlyEntityCell(entity_cell.EntityCell):
    def render_html(self, entity, user):
        return _('(preview not available)')

    def render_csv(self, entity, user):
        return ''


@reports_cells_registry
class ReportEntityCellRelated(_ReportOnlyEntityCell):
    type_id = 'related'

    def __init__(self, model, related_name, related_field):
        super().__init__(model=model, value=related_name)
        self.related_field = related_field

    @classmethod
    def build(cls,
              model: Type[CremeEntity],
              related_name: str,
              ) -> Optional['ReportEntityCellRelated']:
        rel_field = RHRelated._get_related_field(model, related_name)  # TODO: make public ?

        if rel_field is None:
            return None

        return cls(
            model=model,
            related_name=related_name,
            related_field=rel_field,
        )

    @property
    def title(self):
        return str(self.related_field.related_model._meta.verbose_name)


class _ReportEntityCellAggregate(_ReportOnlyEntityCell):
    aggregation_registry = field_aggregation_registry

    def __init__(self, model, agg_id, aggregation):
        super().__init__(model=model, value=agg_id)
        self.aggregation = aggregation


# TODO: factorise with RHAggregate & RHAggregateRegularField
@reports_cells_registry
class ReportEntityCellRegularAggregate(_ReportEntityCellAggregate):
    type_id = 'regular_aggregate'

    def __init__(self, model, agg_id, field, aggregation):
        super().__init__(model=model, agg_id=agg_id, aggregation=aggregation)
        self.field = field

    @classmethod
    def build(cls, model, aggregated_field_name):
        try:
            field_name, aggregation_id = aggregated_field_name.split('__', 1)
        except ValueError:
            logging.warning(
                'ReportEntityCellRegularAggregate.build(): '
                'the aggregated field "%s" is not valid.',
                aggregated_field_name,
            )
            return None

        aggregation = cls.aggregation_registry.get(aggregation_id)

        if aggregation is None:
            logging.warning(
                'ReportEntityCellRegularAggregate.build(): '
                'the aggregation "%s" is not valid.',
                aggregation_id,
            )
            return None

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist as e:
            logging.warning(
                'ReportEntityCellRegularAggregate.build(): '
                'the field "%s" is not valid (%s).',
                field_name, e,
            )
            return None

        if not cls.aggregation_registry.is_regular_field_allowed(field):
            logging.warning(
                'ReportEntityCellRegularAggregate.build(): '
                'this type of field can not be aggregated: %s.',
                field_name,
            )
            return None

        return cls(
            model=model,
            agg_id=aggregated_field_name,
            field=field,
            aggregation=aggregation,
        )

    @property
    def title(self):
        return f'{self.aggregation.title} - {self.field.verbose_name}'


# TODO: factorise (ReportEntityCellCustomAggregate, EntityCellCustomField)
@reports_cells_registry
class ReportEntityCellCustomAggregate(_ReportEntityCellAggregate):
    type_id = 'custom_aggregate'

    def __init__(self, model, agg_id, custom_field, aggregation):
        super().__init__(model=model, agg_id=agg_id, aggregation=aggregation)
        self.custom_field = custom_field

    @classmethod
    def build(cls, model, aggregated_field_name):
        try:
            cfield_id, aggregation_id = aggregated_field_name.split('__', 1)
        except ValueError:
            logging.warning(
                'ReportEntityCellCustomAggregate.build(): '
                'the aggregated field "%s" is not valid.',
                aggregated_field_name,
            )
            return None

        aggregation = cls.aggregation_registry.get(aggregation_id)

        if aggregation is None:
            logging.warning(
                'ReportEntityCellCustomAggregate.build(): '
                'the aggregation "%s" is not valid.',
                aggregation_id,
            )
            return None

        try:
            cfield = CustomField.objects.get_for_model(model)[int(cfield_id)]
        except (KeyError, ValueError):
            logger.warning(
                'ReportEntityCellCustomAggregate: '
                'custom field id="%s" (on model %s) does not exist',
                cfield_id, model,
            )
            return None

        if not cls.aggregation_registry.is_custom_field_allowed(cfield):
            logging.warning(
                'ReportEntityCellCustomAggregate.build(): '
                'this type of custom field can not be aggregated: %s.',
                cfield,
            )
            return None

        return cls(
            model=model,
            agg_id=aggregated_field_name,
            custom_field=cfield,
            aggregation=aggregation,
        )

    @property
    def title(self):
        return f'{self.aggregation.title} - {self.custom_field.name}'


_CELL_2_HAND_MAP = {
    entity_cell.EntityCellRegularField.type_id:     constants.RFT_FIELD,
    entity_cell.EntityCellCustomField.type_id:      constants.RFT_CUSTOM,
    entity_cell.EntityCellFunctionField.type_id:    constants.RFT_FUNCTION,
    entity_cell.EntityCellRelation.type_id:         constants.RFT_RELATION,

    ReportEntityCellRelated.type_id:            constants.RFT_RELATED,
    ReportEntityCellRegularAggregate.type_id:   constants.RFT_AGG_FIELD,
    ReportEntityCellCustomAggregate.type_id:    constants.RFT_AGG_CUSTOM,
}
_HAND_2_CELL_MAP = {v: k for k, v in _CELL_2_HAND_MAP.items()}


# class ReportCreateForm(CremeEntityForm):
#     hf = core_fields.AjaxModelChoiceField(
#         label=_('Existing view'),
#         queryset=HeaderFilter.objects.none(),
#         required=False,
#         help_text=_(
#             'If you select a view of list, '
#             'the columns of the report will be copied from it.'
#         ),
#     )
#     filter = core_fields.AjaxModelChoiceField(
#         label=_('Filter'), queryset=EntityFilter.objects.none(), required=False,
#     )
#
#     class Meta(CremeEntityForm.Meta):
#         model = Report
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ReportCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#     def clean(self):
#         cleaned_data = super().clean()
#
#         if not self._errors:
#             get_data = cleaned_data.get
#             ct = get_data('ct')
#
#             hf = get_data('hf')
#             if hf and not hf.can_view(self.user, ct)[0]:
#                 self.add_error(
#                     'hf',
#                     _(
#                         'Select a valid choice. '
#                         'That choice is not one of the available choices.'
#                     )
#                 )
#
#             efilter = get_data('filter')
#             if efilter and not efilter.can_view(self.user, ct)[0]:
#                 self.add_error(
#                     'filter',
#                     _(
#                         'Select a valid choice. '
#                         'That choice is not one of the available choices.'
#                     ),
#                 )
#
#         return cleaned_data
#
#     @atomic
#     def save(self, *args, **kwargs):
#         report = super().save(*args, **kwargs)
#         hf = self.cleaned_data['hf']
#
#         if hf is not None:
#             build_field = partial(Field.objects.create, report=report)
#
#             for i, cell in enumerate(self.cleaned_data['hf'].filtered_cells, start=1):
#                 build_field(
#                     name=cell.value, order=i,
#                     type=_CELL_2_HAND_MAP[cell.type_id],
#                 )
#
#         return report


# class ReportEditForm(CremeEntityForm):
#     class Meta:
#         model = Report
#         exclude = (*CremeEntityForm.Meta.exclude, 'ct')
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ReportEditForm is deprecated.', DeprecationWarning)
#
#         super().__init__(*args, **kwargs)
#         fields = self.fields
#         filter_f = fields['filter']
#         filter_f.empty_label = pgettext_lazy('creme_core-filter', 'All')
#         filter_f.queryset = filter_f.queryset.filter(entity_type=self.instance.ct)
#
#         efilter = self.instance.filter
#
#         if efilter and not efilter.can_view(self.user)[0]:
#             fields['filter_label'] = core_fields.ReadonlyMessageField(
#                 label=fields['filter'].label,
#                 initial=_('The filter cannot be changed because it is private.'),
#             )
#             del fields['filter']


class LinkFieldToReportForm(CremeForm):
    report = core_fields.CreatorEntityField(
        label=_('Sub-report linked to the column'), model=Report,
    )

    def __init__(self, instance, ctypes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        report = instance.report
        q_filter = ~Q(id__in=[r.id for r in chain(report.get_ascendants_reports(), [report])])

        if ctypes:
            q_filter &= Q(ct__in=[ct.id for ct in ctypes])

        self.fields['report'].q_filter = q_filter

    def save(self):
        rfield = self.instance
        rfield.sub_report = self.cleaned_data['report']

        # We could have a race condition here (so have several Field with selected=True)
        # but it is managed by the 'Report.columns' property
        rfield.selected = not rfield.report.fields.filter(sub_report__isnull=False).exists()
        rfield.save()

        return rfield


# Fields form ------------------------------------------------------------------

class ReportEntityCellRelatedWidget(hf_form.UniformEntityCellsWidget):
    template_name = 'reports/forms/widgets/report-hands/related.html'
    type_id = ReportEntityCellRelated.type_id


class ReportEntityCellRegularAggregatesWidget(hf_form.UniformEntityCellsWidget):
    template_name = 'reports/forms/widgets/report-hands/regular-aggregates.html'
    type_id = ReportEntityCellRegularAggregate.type_id


class ReportEntityCellCustomAggregatesWidget(hf_form.UniformEntityCellsWidget):
    template_name = 'reports/forms/widgets/report-hands/custom-aggregates.html'
    type_id = ReportEntityCellCustomAggregate.type_id


class ReportHandsWidget(hf_form.EntityCellsWidget):
    template_name = 'reports/forms/widgets/report-hands/widget.html'


class ReportEntityCellRegularFieldsField(hf_form.EntityCellRegularFieldsField):
    def _regular_fields_enum(self, model):
        fields = super()._regular_fields_enum(model)
        fields.filter(
            # lambda field, depth: not (
            lambda model, field, depth: not (
                depth
                and field.is_relation
                and issubclass(field.remote_field.model, CremeEntity)
            )
        )

        return fields


# TODO: add a similar EntityCell type in creme_core (& so move this code in core) ??
class ReportEntityCellRelatedField(hf_form.UniformEntityCellsField):
    widget = ReportEntityCellRelatedWidget
    cell_class = ReportEntityCellRelated

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class
        # TODO: can we just use the regular introspection (+ field tags ?) instead
        allowed_fields = model.allowed_related

        get_fields = model._meta.get_fields
        related_fields = (
            f
            for f in get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created
        )
        # TODO ??
        # m2m_fields = (
        #     f
        #     for f in get_fields(include_hidden=True)
        #     if f.many_to_many and f.auto_created
        # )
        # for f in chain(related_fields, m2m_fields)
        for field in related_fields:
            if field.name in allowed_fields:
                cell = cell_class(
                    model=model,
                    related_name=field.name,
                    related_field=field,
                )

                yield cell.key, cell


class ReportEntityCellRegularAggregatesField(hf_form.UniformEntityCellsField):
    widget = ReportEntityCellRegularAggregatesWidget
    cell_class = ReportEntityCellRegularAggregate

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class
        is_field_hidden = FieldsConfig.objects.get_for_model(model).is_field_hidden
        non_hiddable_cells = self._non_hiddable_cells
        aggregation_registry = cell_class.aggregation_registry
        enumerator = ModelFieldEnumerator(
            # model, deep=0,
            model, depth=0,
        ).filter(
            # (lambda f, deep: isinstance(f, aggregation_registry.authorized_fields)),
            (
                lambda model, field, depth:
                isinstance(field, aggregation_registry.authorized_fields)
            ),
            viewable=True,   # TODO: test
        )

        for aggregate in aggregation_registry.aggregations:
            pattern_fmt = aggregate.pattern.format

            for fields_chain in enumerator:
                field = fields_chain[0]
                cell = cell_class(
                    model=model,
                    agg_id=pattern_fmt(field.name),
                    field=field,
                    aggregation=aggregate,
                )

                if not is_field_hidden(field) or cell in non_hiddable_cells:
                    yield cell.key, cell


class ReportEntityCellCustomAggregatesField(hf_form.UniformEntityCellsField):
    widget = ReportEntityCellCustomAggregatesWidget
    cell_class = ReportEntityCellCustomAggregate

    def _get_options(self):
        model = self.model
        cell_class = self.cell_class
        cfield_allowed = cell_class.aggregation_registry.is_custom_field_allowed
        non_hiddable_cells = self._non_hiddable_cells

        # NB: we use the cache of CustomField as EntityCellCustomFieldsField
        agg_custom_fields = [
            cfield
            for cfield in CustomField.objects.get_for_model(self.model).values()
            if cfield_allowed(cfield)
        ]

        for aggregate in cell_class.aggregation_registry.aggregations:
            pattern_fmt = aggregate.pattern.format

            for cf in agg_custom_fields:
                cell = cell_class(
                    model=model,
                    agg_id=pattern_fmt(cf.id),
                    custom_field=cf,
                    aggregation=aggregate,
                )

                if not cf.is_deleted or cell in non_hiddable_cells:
                    yield cell.key, cell


class ReportHandsField(hf_form.EntityCellsField):
    widget: Type[ReportHandsWidget] = ReportHandsWidget

    field_classes = {
        ReportEntityCellRegularFieldsField,
        hf_form.EntityCellCustomFieldsField,
        hf_form.EntityCellFunctionFieldsField,
        hf_form.EntityCellRelationsField,
        ReportEntityCellRelatedField,
        ReportEntityCellRegularAggregatesField,
        ReportEntityCellCustomAggregatesField,
    }

    def __init__(self, *, cell_registry=None, **kwargs):
        super().__init__(
            cell_registry=cell_registry or reports_cells_registry,
            **kwargs
        )


class ReportFieldsForm(CremeForm):
    columns = ReportHandsField(label=_('Columns'))

    def __init__(self, instance, *args, **kwargs):
        self.report = instance
        super().__init__(*args, **kwargs)

        model = instance.ct.model_class()
        cells = reports_cells_registry.build_cells_from_dicts(
            model=model,
            dicts=[
                {
                    'type': _HAND_2_CELL_MAP[column.type],
                    'value': column.name,
                }
                for column in instance.columns
                if column.hand  # Check validity
            ],
        )[0]

        columns_f = self.fields['columns']
        columns_f.non_hiddable_cells = cells
        columns_f.model = model
        columns_f.initial = cells

    def _get_sub_report_n_selected(self, rfields, new_rfield):
        ftype = new_rfield.type
        fname = new_rfield.name

        for rfield in rfields:
            if rfield.type == ftype and rfield.name == fname:
                return rfield.sub_report, rfield.selected

        return None, False

    @atomic
    def save(self):
        report = self.report
        old_rfields = report.columns
        old_ids = [rfield.id for rfield in old_rfields]
        sub_report_n_selected = self._get_sub_report_n_selected

        for i, cell in enumerate(self.cleaned_data['columns'], start=1):
            rfield = Field(
                id=old_ids.pop(0) if old_ids else None,
                report=report, name=cell.value,
                type=_CELL_2_HAND_MAP[cell.type_id],
                order=i,
            )
            rfield.sub_report, rfield.selected = sub_report_n_selected(old_rfields, rfield)

            rfield.save()  # TODO: only if different from the old one

        Field.objects.filter(pk__in=old_ids).delete()

# Fields form [end] ------------------------------------------------------------


class HeaderFilterStep(CremeForm):
    header_filter = forms.ModelChoiceField(
        label=_('Existing view'),
        queryset=HeaderFilter.objects.none(),
        required=False,
        help_text=_(
            'If you select a view of list, '
            'the columns of the report will be copied from it.'
        ),
    )

    def __init__(self, report, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['header_filter'].queryset = HeaderFilter.objects.filter_by_user(
            user=self.user,
        ).filter(
            entity_type=report.ct,
        )


# TODO: factorise with ReportFieldsForm ??
class ReportFieldsStep(CremeForm):
    columns = ReportHandsField(label=_('Columns'))

    def __init__(self, report, cells=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.report = report

        columns_f = self.fields['columns']
        columns_f.model = report.ct.model_class()
        columns_f.initial = cells

    # TODO: @atomic  ?
    def save(self):
        report = self.report
        assert report.pk

        Field.objects.bulk_create([
            Field(
                report=report,
                name=cell.value,
                type=_CELL_2_HAND_MAP[cell.type_id],
                order=i,
            ) for i, cell in enumerate(self.cleaned_data['columns'], start=1)
        ])


class ReportExportPreviewFilterForm(CremeForm):
    doc_type = forms.ChoiceField(label=_('Extension'), required=False, choices=())
    date_field = forms.ChoiceField(label=_('Date field'), required=False, choices=())
    date_filter = core_fields.DateRangeField(label=_('Date filter'), required=False)

    error_messages = {
        'custom_start': _(
            'If you chose a Date field, and select «customized» '
            'you have to specify a start date and/or an end date.'
        ),
    }

    # TODO: rename "report" to "instance" to be consistent ?
    def __init__(self, report, export_registry=export_backend_registry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = export_registry
        fields = self.fields

        fields['date_field'].choices = self._date_field_choices(report)
        fields['date_field'].initial = 'current_month'

        fields['doc_type'].choices = self._backend_choices()

    def _date_field_choices(self, report):
        return [
            ('', pgettext_lazy('reports-date_filter', 'None')),
            *(
                (field.name, field.verbose_name)
                for field in report.ct.model_class()._meta.fields
                if is_date_field(field)
            ),
        ]

    def _backend_choices(self):
        return [
            (backend.id, backend.verbose_name)
            for backend in self.registry.backend_classes
        ]

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('date_field'):
            date_filter = cleaned_data.get('date_filter')

            if not date_filter or not any(date_filter.get_dates(now())):
                raise ValidationError(
                    self.error_messages['custom_start'],
                    code='custom_start',
                )

        return cleaned_data

    def get_q(self):
        cleaned_data = self.cleaned_data
        date_field = cleaned_data['date_field']
        date_filter = cleaned_data['date_filter']

        if date_field:
            return Q(**date_filter.get_q_dict(date_field, now()))

        return None

    def get_backend(self):
        backend_cls = self.registry.get_backend_class(self.cleaned_data['doc_type'])
        return backend_cls() if backend_cls else None

    def export_url_data(self):
        cleaned_data = self.cleaned_data
        date_field = cleaned_data['date_field']
        date_filter = cleaned_data['date_filter']

        data = [
            ('doc_type',   cleaned_data['doc_type']),
            ('date_field', date_field),
        ]

        if date_filter is not None:
            d_range = date_filter.name
            start, end = date_filter.get_dates(now())

            data.extend([
                ('date_filter_0', d_range),
                ('date_filter_1', start.strftime('%d-%m-%Y') if start else ''),
                ('date_filter_2', end.strftime('%d-%m-%Y') if end else ''),
            ])

        return '&'.join(f'{key}={value}' for key, value in data)


class ReportExportFilterForm(ReportExportPreviewFilterForm):
    def __init__(self, instance, *args, **kwargs):
        super().__init__(instance, *args, **kwargs)
        self.fields['doc_type'].required = True

    # TODO ?
    # def save(self):
    #     return self.instance
