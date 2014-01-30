# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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
#import logging

from django.db.transaction import commit_on_success
from django.forms.fields import ChoiceField
from django.db.models import ForeignKey, ManyToManyField
from django.forms.util import ErrorList
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.core.entity_cell import (EntityCell, EntityCellRegularField,
        EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
from creme.creme_core.forms import CremeEntityForm, CremeForm
from creme.creme_core.forms.header_filter import EntityCellsField, EntityCellsWidget
from creme.creme_core.forms.fields import AjaxModelChoiceField, CreatorEntityField, DateRangeField
from creme.creme_core.models import HeaderFilter, EntityFilter
from creme.creme_core.registry import export_backend_registry
from creme.creme_core.utils.meta import get_date_fields, ModelFieldEnumerator

from ..constants import RFT_FIELD, RFT_RELATION, RFT_CUSTOM, RFT_FUNCTION, RFT_AGGREGATE, RFT_RELATED
from ..utils import encode_datetime
from ..models import Report, Field
from ..report_aggregation_registry import field_aggregation_registry


#logger = logging.getLogger(__name__)


#No need to validate (only built by form that does validation for us).
class _EntityCellRelated(EntityCell):
    type_id = 'related'

    def __init__(self, agg_id):
        super(_EntityCellRelated, self).__init__(value=agg_id, title='Related')

class _EntityCellAggregate(EntityCell):
    type_id = 'regular_aggregate'

    def __init__(self, agg_id):
        super(_EntityCellAggregate, self).__init__(value=agg_id, title='Aggregate')

class _EntityCellCustomAggregate(EntityCell):
    type_id = 'custom_aggregate'

    def __init__(self, agg_id):
        super(_EntityCellCustomAggregate, self).__init__(value=agg_id, title='Custom Aggregate')


_CELL_2_HAND_MAP = {
    EntityCellRegularField.type_id:     RFT_FIELD,
    EntityCellCustomField.type_id:      RFT_CUSTOM,
    EntityCellFunctionField.type_id:    RFT_FUNCTION,
    EntityCellRelation.type_id:         RFT_RELATION,
    _EntityCellRelated.type_id:         RFT_RELATED,
    _EntityCellAggregate.type_id:       RFT_AGGREGATE,
    _EntityCellCustomAggregate.type_id: RFT_AGGREGATE,
}
_HAND_2_CELL_MAP = dict((v,k) for k, v in _CELL_2_HAND_MAP.iteritems())

_RELATED_PREFIX     = _EntityCellRelated.type_id + '-'
_REGULAR_AGG_PREFIX = _EntityCellAggregate.type_id + '-'
_CUSTOM_AGG_PREFIX  = _EntityCellCustomAggregate.type_id + '-'


class ReportCreateForm(CremeEntityForm):
    hf     = AjaxModelChoiceField(label=_(u"Existing view"), queryset=HeaderFilter.objects.none(),
                                  help_text=_('The columns of the report will be copied from the list view.')
                                 )
    filter = AjaxModelChoiceField(label=_(u"Filter"), queryset=EntityFilter.objects.none(), required=False)

    class Meta(CremeEntityForm.Meta):
        model = Report

    def clean(self):
        cleaned_data = super(ReportCreateForm, self).clean()

        if not self._errors:
            get_data = cleaned_data.get
            ct = get_data('ct')
            hf = get_data('hf')

            if hf.entity_type != ct:
                self.errors['hf'] = ErrorList([ugettext(u'Select a valid choice. That choice is not one of the available choices.')])

            efilter = get_data('filter')
            if efilter and efilter.entity_type != ct:
                self.errors['filter'] = ErrorList([ugettext(u'Select a valid choice. That choice is not one of the available choices.')])

        return cleaned_data

    @commit_on_success
    def save(self, *args, **kwargs):
        report = super(ReportCreateForm, self).save(*args, **kwargs)
        build_field = partial(Field.objects.create, report=report)

        for i, cell in enumerate(self.cleaned_data['hf'].cells, start=1):
            #TODO: check in clean() that id is OK
            build_field(name=cell.value, title=cell.title, order=i,
                        type=_CELL_2_HAND_MAP[cell.type_id],
                       )

        return report


class ReportEditForm(CremeEntityForm):
    class Meta:
        model = Report
        exclude = CremeEntityForm.Meta.exclude + ('ct',)

    def __init__(self, *args, **kwargs):
        super(ReportEditForm, self).__init__(*args, **kwargs)
        filter_f = self.fields['filter']
        filter_f.empty_label = ugettext(u'All')
        filter_f.queryset = filter_f.queryset.filter(entity_type=self.instance.ct)


class LinkFieldToReportForm(CremeForm):
    report = CreatorEntityField(label=_(u"Sub-report linked to the column"), model=Report)

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

        # we could have a race condition here (so have several Field with selected=True)
        # but it is manage by the 'Report.columns' property
        rfield.selected = not rfield.report.fields.filter(sub_report__isnull=False).exists()
        rfield.save()


class ReportHandsWidget(EntityCellsWidget):
    def __init__(self, related_entities=(), *args, **kwargs):
        super(ReportHandsWidget, self).__init__(*args, **kwargs)
        self.related_entities = related_entities
        self.regular_aggregates = ()
        self.custom_aggregates = ()

    def _build_render_context(self, name, value, attrs):
        ctxt = super(ReportHandsWidget, self)._build_render_context(name, value, attrs)
        ctxt['related_entities']   = self.related_entities
        ctxt['regular_aggregates'] = self.regular_aggregates
        ctxt['custom_aggregates']  = self.custom_aggregates

        return ctxt

    def render(self, name, value, attrs=None):
        return render_to_string('reports/reports_hands_widget.html',
                                self._build_render_context( name, value, attrs)
                               )


class ReportHandsField(EntityCellsField):
    widget = ReportHandsWidget

    def _build_4_custom_aggregate(self, model, name):
        return _EntityCellCustomAggregate(name[len(_CUSTOM_AGG_PREFIX):])

    def _build_4_regular_aggregate(self, model, name):
        return _EntityCellAggregate(name[len(_REGULAR_AGG_PREFIX):])

    def _build_4_related(self, model, name):
        return _EntityCellRelated(name[len(_RELATED_PREFIX):])

    def _regular_fields_enum(self, model):
        fields = super(ReportHandsField, self)._regular_fields_enum(model)
        fields.filter(lambda field, depth: not (depth and isinstance(field, (ForeignKey, ManyToManyField))))

        return fields

    @EntityCellsField.content_type.setter
    def content_type(self, ct):
        EntityCellsField.content_type.fset(self, ct)

        #if ct is None:
            #widget.regular_aggregates = ()
        #else:
        if ct is not None:
            builders = self._builders
            widget = self.widget
            model = ct.model_class()

            #Related ---------------------------------------------------------
            widget.related_entities = related_choices = []

            for related_name, related_vname in Report.get_related_fields_choices(model):
                rel_id = _RELATED_PREFIX + related_name
                related_choices.append((rel_id, related_vname))
                builders[rel_id] = ReportHandsField._build_4_related

            #Aggregates ------------------------------------------------------
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
                        agg_id = '%scf__%s__%s' % (_CUSTOM_AGG_PREFIX, cf.field_type, pattern % cf.id)
                        cust_agg_choices.append((agg_id, u'%s - %s' % (title, cf.name)))
                        builders[agg_id] = ReportHandsField._build_4_custom_aggregate


class ReportFieldsForm(CremeForm):
    columns = ReportHandsField(label=_(u'Columns'))

    def __init__(self, entity, *args, **kwargs):
        self.report = entity
        super(ReportFieldsForm, self).__init__(*args, **kwargs)

        columns_f = self.fields['columns']
        columns_f.content_type = entity.ct

        cells = []
        for column in entity.columns:
            #NB: this is a hack : EntityCellWidgets only use value & type_id to check initial data
            #    it would be better to use a method column.hand.to_entity_cell()
            if column.hand: #check validity
                cell = EntityCell(value=column.name)
                cell.type_id = _HAND_2_CELL_MAP[column.type]
                cells.append(cell)

        columns_f.initial = cells

    def _get_sub_report_n_selected(self, rfields, new_rfield):
        ftype = new_rfield.type
        fname = new_rfield.name

        for rfield in rfields:
            if rfield.type == ftype and rfield.name == fname:
                return rfield.sub_report, rfield.selected

        return None, False

    @commit_on_success
    def save(self):
        report = self.report
        old_rfields = report.columns
        old_ids = [rfield.id for rfield in old_rfields]
        sub_report_n_selected = self._get_sub_report_n_selected

        for i, cell in enumerate(self.cleaned_data['columns'], start=1):
            #rfield = Field(id=old_rfields.pop(0).id if old_rfields else None,
            rfield = Field(id=old_ids.pop(0) if old_ids else None,
                           report=report, name=cell.value,
                           type=_CELL_2_HAND_MAP[cell.type_id],
                           order=i,
                          )
            rfield.sub_report, rfield.selected = sub_report_n_selected(old_rfields, rfield)

            rfield.save() #TODO: only if different from the old one

        #Field.objects.filter(pk__in=[rfield.id for rfield in old_rfields]).delete()
        Field.objects.filter(pk__in=old_ids).delete()


class DateReportFilterForm(CremeForm):
    doc_type    = ChoiceField(label=_(u'Extension'), required=False, choices=())
    date_field  = ChoiceField(label=_(u'Date field'), required=False, choices=())
    date_filter = DateRangeField(label=_(u'Date filter'), required=False)

    def __init__(self, report, *args, **kwargs):
        super(DateReportFilterForm, self).__init__(*args, **kwargs)
        fields = self.fields

        date_field_choices = [("", _(u"None"))]
        date_field_choices.extend([(field.name, field.verbose_name)
                                            for field in get_date_fields(report.ct.model_class())
                                       ])
        fields['date_field'].choices = date_field_choices

        choices = [(backend.id, backend.verbose_name)
                        for backend in export_backend_registry.iterbackends()
                  ]
        if choices:
            doc_type = fields['doc_type']
            doc_type.choices = choices
            try:
                doc_type.initial = choices[0][0]
            except IndexError:
                pass

    def get_q_dict(self):
        cdata = self.cleaned_data
        if cdata:
            date_field = cdata['date_field']
            if date_field:
                return cdata['date_filter'].get_q_dict(date_field, now())
        return None

    def get_dates(self):
        cdata = self.cleaned_data
        if cdata and cdata['date_field']:
            date_filter = cdata['date_filter']
            if date_filter:
                return date_filter.get_dates(now())
        return None, None

    def clean(self):
        cdata = super(DateReportFilterForm, self).clean()

        if cdata['date_field']:
            start, end = self.get_dates()
            if not start and not end:
                self.errors['date_filter'] = ErrorList([ugettext(u"If you chose a Date field, and select «customized» you have to specify a start date and/or an end date.")])

        return cdata

    @property
    def forge_url_data(self):
        cdata = self.cleaned_data

        if cdata:
            get_cdata = cdata.get
            date_field = get_cdata('date_field')

            if date_field:
                data = ['field=%s' % date_field,
                        'range_name=%s' % get_cdata('date_filter').name
                       ]

                start, end = self.get_dates()

                if start is not None:
                    data.append('start=%s' % encode_datetime(start))

                if end is not None:
                    data.append('end=%s' % encode_datetime(end))

                return "?%s" % "&".join(data)

        return ""

    #def save(self, *args, **kwargs):
        #return self.cleaned_data
