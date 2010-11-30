
# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from datetime import timedelta

from django.db.models import Min, Max
from django.db.models.fields import (PositiveIntegerField, CharField,
                                     BooleanField, FieldDoesNotExist)
from django.db.models.fields.related import ForeignKey
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _

from creme_core.models.entity import CremeEntity
from creme_core.models.relation import RelationType
from creme_core.models.header_filter import HFI_RELATION, HFI_FIELD

from reports.models.report import Report, report_prefix_url
from reports.report_aggregation_registry import field_aggregation_registry


#ReportGraph types
RGT_DAY    = 1
RGT_MONTH  = 2
RGT_YEAR   = 3
RGT_RANGE  = 4
RGT_FK     = 5

verbose_report_graph_types = {
    RGT_DAY    : _(u"By days"),
    RGT_MONTH  : _(u"By months"),
    RGT_YEAR   : _(u"By years"),
    RGT_RANGE  : _(u"By X days"),
    RGT_FK     : _(u"By values"),
}


class ReportGraph(CremeEntity):
    name     = CharField(_(u'Name of the graph'), max_length=100)
    report   = ForeignKey(Report)
    abscissa = CharField(_(u'Abscissa axis'), max_length=100)
    ordinate = CharField(_(u'Ordinate axis'), max_length=100)
    type     = PositiveIntegerField(_(u'Type'))
    days     = PositiveIntegerField(_(u'Days'), blank=True, null=True)
    is_count = BooleanField(_(u'Make a count instead of aggregate ?'))

    class Meta:
        app_label = 'reports'
        verbose_name = _(u"Report's graph")
        verbose_name_plural  = _(u"Reports' graphs")
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "%s/graph/%s" % (report_prefix_url, self.id)

    def get_edit_absolute_url(self):
        return "%s/graph/edit/%s" % (report_prefix_url, self.id)

    def get_delete_absolute_url(self):
        return "%s/graph/delete/%s" % (report_prefix_url, self.id)

    def fetch(self, extra_q=None, order='ASC'):
        assert order=='ASC' or order=='DESC'
        report        = self.report
        ct            = report.ct
        model         = ct.model_class()
        model_manager = model.objects
        type          = self.type
        abscissa      = self.abscissa
        ordinate      = self.ordinate
        is_count      = self.is_count
        ordinate_col, sep, aggregate = ordinate.rpartition('__')
        aggregate_field = field_aggregation_registry.get(aggregate)
        aggregate_func  = aggregate_field.func if aggregate_field else None#Seems to be a count
        aggregate_col   = aggregate_func(ordinate_col) if aggregate_func else None#Seems to be a count

        if report.filter is not None:
            entities = model_manager.filter(report.filter.get_q())
        else:
            entities = model_manager.all()

        if extra_q is not None:
            entities = entities.filter(extra_q)

        entities_filter = entities.filter

        x, y = [], []

        if type == RGT_DAY:
            x, y = _get_dates_values(entities, abscissa, ordinate, ordinate_col, aggregate_func, entities_filter, 'day', q_func=lambda date: Q(**{'%s__year' % abscissa: date.year}) & Q(**{'%s__month' % abscissa: date.month})  & Q(**{'%s__day' % abscissa: date.day}), date_format="%d/%m/%Y", order=order, is_count=is_count)

        elif type == RGT_MONTH:
            x, y = _get_dates_values(entities, abscissa, ordinate, ordinate_col, aggregate_func, entities_filter, 'month', q_func=lambda date: Q(**{'%s__year' % abscissa: date.year}) & Q(**{'%s__month' % abscissa: date.month}), date_format="%m/%Y", order=order, is_count=is_count)

        elif type == RGT_YEAR:
            x, y = _get_dates_values(entities, abscissa, ordinate, ordinate_col, aggregate_func, entities_filter, 'year', q_func=lambda date: Q(**{'%s__year' % abscissa: date.year}), date_format="%Y", order=order, is_count=is_count)

        elif type == RGT_RANGE:
            min_date = entities.aggregate(min_date=Min(abscissa)).get('min_date')
            max_date = entities.aggregate(max_date=Max(abscissa)).get('max_date')
            days = timedelta(self.days or 1)
            
            if min_date is not None and max_date is not None:
                if order == 'ASC':
                    while min_date <= max_date:
                        begin = min_date
                        end   = min_date + days
                        x.append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")))

                        sub_entities = entities_filter(Q(**{'%s__range' % abscissa: (begin, end)}))
                        if is_count:
                            y.append(sub_entities.count())
                        else:
                            y.append(sub_entities.aggregate(aggregate_col).get(ordinate))
                        min_date = end
                else:
                    while(max_date >= min_date):
                        begin = max_date
                        end   = max_date - days
                        x.append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")))

                        sub_entities = entities_filter(Q(**{'%s__range' % abscissa: (end, begin)}))
                        if is_count:
                            y.append(sub_entities.count())
                        else:
                            y.append(sub_entities.aggregate(aggregate_col).get(ordinate))
                        max_date = end
                
        elif type == RGT_FK:
            
            fk_ids = set(entities.values_list(abscissa, flat=True))#.distinct()
            _fks = entities.model._meta.get_field(abscissa).rel.to.objects.filter(pk__in=fk_ids)
            if order == 'DESC':
                _fks.reverse()#Seems useless on models which haven't ordering
            fks = dict((rel.id, unicode(rel)) for rel in _fks)

            for fk_id in fk_ids:
                x.append(fks.get(fk_id, ''))
                sub_entities = entities_filter(Q(**{'%s' % abscissa: fk_id}))
                if is_count:
                    y.append(sub_entities.count())
                else:
                    y.append(sub_entities.aggregate(aggregate_col).get(ordinate))

        for i, item in enumerate(y):
            if item is None:
                y[i] = 0

        return (x, y)


def _get_dates_values(entities, abscissa, ordinate, ordinate_col, aggregate_func, qfilter, range, q_func=None, date_format=None, order='ASC', is_count=False):
    distinct_dates = entities.dates(abscissa, range, order)
    x, y = [], []
    for date in distinct_dates:
        sub_entities = qfilter(q_func(date))
        x.append(date.strftime(date_format))
        if is_count:
            y.append(sub_entities.count())
        else:
            y.append(sub_entities.aggregate(aggregate_func(ordinate_col)).get(ordinate))

    return x, y

def fetch_graph_from_instance_block(instance_block, entity, order='ASC'):
    volatile_column   = instance_block.data

    graph             = instance_block.entity.get_real_entity()
    report            = graph.report
    report_model      = report.ct.model_class()

    model             = entity.__class__
    ct_entity         = entity.entity_type #entity should always be a CremeEntity because graphs can be created only on CremeEntities
    
    columns = volatile_column.split('#')
    volatile_column, hfi_type = (columns[0], columns[1]) if columns[0] else ('', 0)

    try:
        hfi_type = int(hfi_type)
    except ValueError:
        hfi_type = 0

    x, y = [], []

    if hfi_type == HFI_FIELD:
        try:
            field = report_model._meta.get_field(volatile_column)
            if field.get_internal_type() == 'ForeignKey' and field.rel.to == model:
                x, y = graph.fetch(extra_q=Q(**{'%s__pk' % volatile_column: entity.pk}), order=order)
        except FieldDoesNotExist:
            pass

    elif hfi_type == HFI_RELATION:
        try:
            rt=RelationType.objects.get(pk=volatile_column)
            obj_ctypes = rt.object_ctypes.all()

            if not obj_ctypes or ct_entity in obj_ctypes:
                extra_q = Q(**{'relations__type__pk': volatile_column}) & Q(**{'relations__object_entity__pk' : entity.pk})
                x, y = graph.fetch(extra_q=extra_q, order=order)

        except RelationType.DoesNotExist:
            pass

    else:
        x, y = graph.fetch(order=order)
        
    return (x, y)