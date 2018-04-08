# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from functools import partial
from itertools import chain

from django.core.exceptions import ValidationError
from django.db.models import ForeignKey, ManyToManyField
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.forms.fields import ChoiceField, CharField
# from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.backends import export_backend_registry
from creme.creme_core.core.entity_cell import (EntityCell, EntityCellRegularField,
        EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
from creme.creme_core.forms import CremeEntityForm, CremeForm
from creme.creme_core.forms.fields import AjaxModelChoiceField, CreatorEntityField, DateRangeField
from creme.creme_core.forms.header_filter import EntityCellsField, EntityCellsWidget
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import CremeEntity, HeaderFilter, EntityFilter
from creme.creme_core.utils.meta import ModelFieldEnumerator, is_date_field

from .. import constants, get_report_model
from ..models import Field
from ..report_aggregation_registry import field_aggregation_registry


Report = get_report_model()


# NB: No need to validate (only built by form that does validation for us).
class _EntityCellRelated(EntityCell):
    type_id = 'related'

    # def __init__(self, agg_id):
    #     super(_EntityCellRelated, self).__init__(value=agg_id, title='Related')
    def __init__(self, model, agg_id):
        super(_EntityCellRelated, self).__init__(model=model, value=agg_id, title='Related')


class _EntityCellAggregate(EntityCell):
    type_id = 'regular_aggregate'

    # def __init__(self, agg_id):
    #     super(_EntityCellAggregate, self).__init__(value=agg_id, title='Aggregate')
    def __init__(self, model, agg_id):
        super(_EntityCellAggregate, self).__init__(model=model, value=agg_id, title='Aggregate')


class _EntityCellCustomAggregate(EntityCell):
    type_id = 'custom_aggregate'

    # def __init__(self, agg_id):
    #     super(_EntityCellCustomAggregate, self).__init__(value=agg_id, title='Custom Aggregate')
    def __init__(self, model, agg_id):
        super(_EntityCellCustomAggregate, self).__init__(model=model, value=agg_id, title='Custom Aggregate')


_CELL_2_HAND_MAP = {
    EntityCellRegularField.type_id:     constants.RFT_FIELD,
    EntityCellCustomField.type_id:      constants.RFT_CUSTOM,
    EntityCellFunctionField.type_id:    constants.RFT_FUNCTION,
    EntityCellRelation.type_id:         constants.RFT_RELATION,
    _EntityCellRelated.type_id:         constants.RFT_RELATED,
    _EntityCellAggregate.type_id:       constants.RFT_AGG_FIELD,
    _EntityCellCustomAggregate.type_id: constants.RFT_AGG_CUSTOM,
}
_HAND_2_CELL_MAP = {v: k for k, v in _CELL_2_HAND_MAP.iteritems()}

_RELATED_PREFIX     = _EntityCellRelated.type_id + '-'
_REGULAR_AGG_PREFIX = _EntityCellAggregate.type_id + '-'
_CUSTOM_AGG_PREFIX  = _EntityCellCustomAggregate.type_id + '-'


class ReportCreateForm(CremeEntityForm):
    hf     = AjaxModelChoiceField(label=_(u'Existing view'), queryset=HeaderFilter.objects.none(),
                                  required=False,
                                  help_text=_(u'If you select a view of list, '
                                              u'the columns of the report will be copied from it.'
                                             ),
                                 )
    filter = AjaxModelChoiceField(label=_(u'Filter'), queryset=EntityFilter.objects.none(), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Report

    def clean(self):
        cleaned_data = super(ReportCreateForm, self).clean()

        if not self._errors:
            get_data = cleaned_data.get
            ct = get_data('ct')

            hf = get_data('hf')
            if hf and not hf.can_view(self.user, ct)[0]:
                self.add_error('hf', _(u'Select a valid choice. That choice is not one of the available choices.'))

            efilter = get_data('filter')
            if efilter and not efilter.can_view(self.user, ct)[0]:
                self.add_error('filter', _(u'Select a valid choice. That choice is not one of the available choices.'))

        return cleaned_data

    @atomic
    def save(self, *args, **kwargs):
        report = super(ReportCreateForm, self).save(*args, **kwargs)
        hf = self.cleaned_data['hf']

        if hf is not None:
            build_field = partial(Field.objects.create, report=report)

            for i, cell in enumerate(self.cleaned_data['hf'].filtered_cells, start=1):
                # TODO: check in clean() that id is OK
                build_field(name=cell.value, order=i,  # title=cell.title
                            type=_CELL_2_HAND_MAP[cell.type_id],
                           )

        return report


class ReportEditForm(CremeEntityForm):
    class Meta:
        model = Report
        exclude = CremeEntityForm.Meta.exclude + ('ct',)

    def __init__(self, *args, **kwargs):
        super(ReportEditForm, self).__init__(*args, **kwargs)
        fields = self.fields
        filter_f = fields['filter']
        filter_f.empty_label = ugettext(u'All')
        filter_f.queryset = filter_f.queryset.filter(entity_type=self.instance.ct)

        efilter = self.instance.filter

        if efilter and not efilter.can_view(self.user)[0]:
            fields['filter_label'] = CharField(label=fields['filter'].label,
                                               required=False, widget=Label,
                                               initial=_(u'The filter cannot be changed because it is private.'),
                                              )
            del fields['filter']


class LinkFieldToReportForm(CremeForm):
    report = CreatorEntityField(label=_(u'Sub-report linked to the column'), model=Report)

    def __init__(self, field, ctypes, *args, **kwargs):
        super(LinkFieldToReportForm, self).__init__(*args, **kwargs)
        self.rfield = field
        report = field.report
        q_filter = {'~id__in': [r.id for r in chain(report.get_ascendants_reports(), [report])]}

        if ctypes:
            q_filter['ct__in'] = [ct.id for ct in ctypes]

        self.fields['report'].q_filter = q_filter

    def save(self):
        rfield = self.rfield
        rfield.sub_report = self.cleaned_data['report']

        # We could have a race condition here (so have several Field with selected=True)
        # but it is managed by the 'Report.columns' property
        rfield.selected = not rfield.report.fields.filter(sub_report__isnull=False).exists()
        rfield.save()


class ReportHandsWidget(EntityCellsWidget):
    template_name = 'reports/forms/widgets/report-hands.html'

    def __init__(self, related_entities=(), *args, **kwargs):
        super(ReportHandsWidget, self).__init__(*args, **kwargs)
        self.related_entities = related_entities
        self.regular_aggregates = ()
        self.custom_aggregates = ()

    # def _build_render_context(self, name, value, attrs):
    #     ctxt = super(ReportHandsWidget, self)._build_render_context(name, value, attrs)
    #     ctxt['related_entities']   = self.related_entities
    #     ctxt['regular_aggregates'] = self.regular_aggregates
    #     ctxt['custom_aggregates']  = self.custom_aggregates
    #
    #     return ctxt

    # def render(self, name, value, attrs=None):
    #     return render_to_string('reports/reports_hands_widget.html',
    #                             self._build_render_context( name, value, attrs)
    #                            )

    def get_context(self, name, value, attrs):
        context = super(ReportHandsWidget, self).get_context(name=name, value=value, attrs=attrs)

        widget_cxt = context['widget']
        widget_cxt['related_entities']   = self.related_entities
        widget_cxt['regular_aggregates'] = self.regular_aggregates
        widget_cxt['custom_aggregates']  = self.custom_aggregates

        return context


class ReportHandsField(EntityCellsField):
    widget = ReportHandsWidget

    def _build_4_custom_aggregate(self, model, name):
        return _EntityCellCustomAggregate(model, name[len(_CUSTOM_AGG_PREFIX):])

    def _build_4_regular_aggregate(self, model, name):
        return _EntityCellAggregate(model, name[len(_REGULAR_AGG_PREFIX):])

    def _build_4_related(self, model, name):
        return _EntityCellRelated(model, name[len(_RELATED_PREFIX):])

    def _regular_fields_enum(self, model):
        fields = super(ReportHandsField, self)._regular_fields_enum(model)
        fields.filter(lambda field, depth: not (depth and isinstance(field, (ForeignKey, ManyToManyField))
                                                # and issubclass(field.rel.to, CremeEntity)
                                                and issubclass(field.remote_field.model, CremeEntity)
                                               )
                     )

        return fields

    @EntityCellsField.content_type.setter
    def content_type(self, ct):
        EntityCellsField.content_type.fset(self, ct)

        if ct is not None:
            builders = self._builders
            widget = self.widget
            model = ct.model_class()

            # Related ----------------------------------------------------------
            widget.related_entities = related_choices = []

            for related_name, related_vname in Report.get_related_fields_choices(model):
                rel_id = _RELATED_PREFIX + related_name
                related_choices.append((rel_id, related_vname))
                builders[rel_id] = ReportHandsField._build_4_related

            # Aggregates -------------------------------------------------------
            widget.regular_aggregates = reg_agg_choices = []
            widget.custom_aggregates  = cust_agg_choices = []
            authorized_fields       = field_aggregation_registry.authorized_fields
            authorized_customfields = field_aggregation_registry.authorized_customfields

            for aggregate in field_aggregation_registry.itervalues():
                pattern = aggregate.pattern
                title   = aggregate.title

                for f_name, f_vname in ModelFieldEnumerator(model, deep=0) \
                                            .filter((lambda f, deep: isinstance(f, authorized_fields)),
                                                    viewable=True,
                                                   ) \
                                            .choices():
                    agg_id = _REGULAR_AGG_PREFIX + pattern % f_name
                    reg_agg_choices.append((agg_id, u'%s - %s' % (title, f_vname)))

                    builders[agg_id] = ReportHandsField._build_4_regular_aggregate

                for cf in self._custom_fields:
                    if cf.field_type in authorized_customfields:
                        agg_id = _CUSTOM_AGG_PREFIX + pattern % cf.id
                        cust_agg_choices.append((agg_id, u'%s - %s' % (title, cf.name)))
                        builders[agg_id] = ReportHandsField._build_4_custom_aggregate


class ReportFieldsForm(CremeForm):
    columns = ReportHandsField(label=_(u'Columns'))

    def __init__(self, entity, *args, **kwargs):
        self.report = entity
        super(ReportFieldsForm, self).__init__(*args, **kwargs)

        cells = []
        model = self.report.ct.model_class()
        for column in entity.columns:
            # TODO: this is a hack : EntityCellWidgets only use value & type_id to check initial data
            #       it would be better to use a method column.hand.to_entity_cell()
            if column.hand:  # Check validity
                if column.type == constants.RFT_FIELD:
                    # Only the non_hiddable_cells with class EntityCellRegularField are used.
                    cell = EntityCellRegularField.build(model=model, name=column.name)
                else:
                    cell = EntityCell(model=model, value=column.name)
                    cell.type_id = _HAND_2_CELL_MAP[column.type]

                cells.append(cell)

        columns_f = self.fields['columns']
        columns_f.non_hiddable_cells = cells
        columns_f.content_type = entity.ct
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
            rfield = Field(id=old_ids.pop(0) if old_ids else None,
                           report=report, name=cell.value,
                           type=_CELL_2_HAND_MAP[cell.type_id],
                           order=i,
                          )
            rfield.sub_report, rfield.selected = sub_report_n_selected(old_rfields, rfield)

            rfield.save()  # TODO: only if different from the old one

        Field.objects.filter(pk__in=old_ids).delete()


class ReportExportPreviewFilterForm(CremeForm):
    doc_type    = ChoiceField(label=_(u'Extension'), required=False, choices=())
    date_field  = ChoiceField(label=_(u'Date field'), required=False, choices=())
    date_filter = DateRangeField(label=_(u'Date filter'), required=False)

    error_messages = {
        'custom_start': _(u'If you chose a Date field, and select «customized» '
                          u'you have to specify a start date and/or an end date.'
                         ),
    }

    def __init__(self, report, *args, **kwargs):
        super(ReportExportPreviewFilterForm, self).__init__(*args, **kwargs)
        fields = self.fields

        fields['date_field'].choices = self._date_field_choices(report)
        fields['date_field'].initial = 'current_month'

        fields['doc_type'].choices = self._backend_choices()

    def _date_field_choices(self, report):
        return chain([('', pgettext_lazy('reports-date_filter', u'None'))],
                     [(field.name, field.verbose_name)
                        for field in report.ct.model_class()._meta.fields
                            if is_date_field(field)
                     ],
                    )

    def _backend_choices(self):
        return [(backend.id, backend.verbose_name)
                    for backend in export_backend_registry.iterbackends()
               ]

    def clean(self):
        cleaned_data = super(ReportExportPreviewFilterForm, self).clean()

        if cleaned_data.get('date_field'):
            date_filter = cleaned_data.get('date_filter')

            if not date_filter or not any(date_filter.get_dates(now())):
                raise ValidationError(self.error_messages['custom_start'],
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
        return export_backend_registry.get_backend(self.cleaned_data['doc_type'])

    def export_url_data(self):
        cleaned_data = self.cleaned_data
        date_field = cleaned_data['date_field']
        date_filter = cleaned_data['date_filter']

        data = [('doc_type',   cleaned_data['doc_type']),
                ('date_field', date_field),
               ]

        if date_filter is not None:
            d_range = date_filter.name
            start, end = date_filter.get_dates(now())

            data.extend([('date_filter_0', d_range),
                         ('date_filter_1', start.strftime('%d-%m-%Y') if start else ''),
                         ('date_filter_2', end.strftime('%d-%m-%Y') if end else ''),
                        ])

        return '&'.join('%s=%s' % (key, value) for key, value in data)


class ReportExportFilterForm(ReportExportPreviewFilterForm):
    def __init__(self, report, *args, **kwargs):
        super(ReportExportFilterForm, self).__init__(report, *args, **kwargs)
        self.fields['doc_type'].required = True
