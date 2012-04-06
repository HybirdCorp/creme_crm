# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.db.models import PositiveIntegerField, CharField, BooleanField, ForeignKey, FieldDoesNotExist, Min, Max
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _, ugettext

from creme_core.models import CremeEntity, RelationType, Relation, InstanceBlockConfigItem
from creme_core.models.header_filter import HFI_RELATION, HFI_FIELD
from creme_core.utils.meta import get_verbose_field_name

from reports.models.report import Report
from reports.report_aggregation_registry import field_aggregation_registry


#ReportGraph types
RGT_DAY      = 1
RGT_MONTH    = 2
RGT_YEAR     = 3
RGT_RANGE    = 4
RGT_FK       = 5
RGT_RELATION = 6

verbose_report_graph_types = {
    RGT_DAY      : _(u"By days"),
    RGT_MONTH    : _(u"By months"),
    RGT_YEAR     : _(u"By years"),
    RGT_RANGE    : _(u"By X days"),
    RGT_FK       : _(u"By values"),
    RGT_RELATION : _(u"By values"),
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
        verbose_name_plural = _(u"Reports' graphs")
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/reports/graph/%s" % self.id

    def get_edit_absolute_url(self):
        return "/reports/graph/edit/%s" % self.id

    def get_related_entity(self):
        return self.report

    def fetch(self, extra_q=None, order='ASC'):
        assert order=='ASC' or order=='DESC'
        report        = self.report
        ct            = report.ct
        model         = ct.model_class()
        model_manager = model.objects
        gtype         = self.type
        abscissa      = self.abscissa
        ordinate      = self.ordinate
        is_count      = self.is_count
        ordinate_col, sep, aggregate = ordinate.rpartition('__')
        aggregate_field = field_aggregation_registry.get(aggregate)
        aggregate_func  = aggregate_field.func if aggregate_field else None #Seems to be a count
        aggregate_col   = aggregate_func(ordinate_col) if aggregate_func else None #Seems to be a count

        entities = model_manager.all()

        if report.filter is not None:
            entities = (report.filter.filter(entities))

        if extra_q is not None:
            entities = entities.filter(extra_q)

        entities_filter = entities.filter

        x, y = [], []
        x_append = x.append
        y_append = y.append

        #TODO: map of function ???
        if gtype == RGT_DAY:
            x, y = _get_dates_values(entities, abscissa, ordinate, ordinate_col,
                                     aggregate_func, entities_filter, 'day',
                                     q_func=lambda date: Q(**{str('%s__year' % abscissa): date.year}) & Q(**{str('%s__month' % abscissa): date.month}) & Q(**{str('%s__day' % abscissa): date.day}),
                                     date_format="%d/%m/%Y", order=order, is_count=is_count
                                    )

        elif gtype == RGT_MONTH:
            x, y = _get_dates_values(entities, abscissa, ordinate, ordinate_col,
                                     aggregate_func, entities_filter, 'month',
                                     q_func=lambda date: Q(**{str('%s__year' % abscissa): date.year}) & Q(**{str('%s__month' % abscissa): date.month}),
                                     date_format="%m/%Y", order=order, is_count=is_count
                                    )
        elif gtype == RGT_YEAR:
            x, y = _get_dates_values(entities, abscissa, ordinate, ordinate_col,
                                     aggregate_func, entities_filter, 'year',
                                     q_func=lambda date: Q(**{str('%s__year' % abscissa): date.year}),
                                     date_format="%Y", order=order, is_count=is_count
                                    )

        elif gtype == RGT_RANGE:
            min_date = entities.aggregate(min_date=Min(abscissa)).get('min_date')
            max_date = entities.aggregate(max_date=Max(abscissa)).get('max_date')
            days = timedelta(self.days or 1)

            if min_date is not None and max_date is not None:
                #TODO: factorise the 2 'while' loops
                if order == 'ASC':
                    while min_date <= max_date:
                        begin = min_date
                        end   = min_date + days
                        x_append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")))

                        sub_entities = entities_filter(Q(**{str('%s__range' % abscissa): (begin, end)}))
                        if is_count:
                            y_append(sub_entities.count())
                        else:
                            y_append(sub_entities.aggregate(aggregate_col).get(ordinate))
                        min_date = end
                else:
                    while max_date >= min_date:
                        begin = max_date
                        end   = max_date - days
                        x_append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")))

                        sub_entities = entities_filter(Q(**{str('%s__range' % abscissa): (end, begin)}))
                        if is_count:
                            y_append(sub_entities.count())
                        else:
                            y_append(sub_entities.aggregate(aggregate_col).get(ordinate))
                        max_date = end

        elif gtype == RGT_FK:
            _fks = entities.model._meta.get_field(abscissa).rel.to.objects.all() #TODO: rename

            if order == 'DESC':
                #_fks.reverse()#Seems useless on models which haven't ordering
                _fks = _fks.reverse()


            for fk in _fks:
                x_append(unicode(fk))
                sub_entities = entities_filter(Q(**{str('%s' % abscissa): fk.id})) #TODO: Q useless ??

                if is_count:
                    y_append(sub_entities.count())
                else:
                    y_append(sub_entities.aggregate(aggregate_col).get(ordinate))

        elif gtype == RGT_RELATION:
            #TODO: Optimize !
            try:
                rt = RelationType.objects.get(pk=abscissa)
            except RelationType.DoesNotExist:
                pass
            else:
                relations = Relation.objects.filter(type=rt, subject_entity__entity_type=ct)

                obj_ids = set(relations.values_list('object_entity__id', flat=True))

                ce_objects_get = CremeEntity.objects.get
                model_objects_filter = model.objects.filter

                for obj_id in obj_ids:
                    try:
                        x_append(unicode(ce_objects_get(pk=obj_id).get_real_entity()))
                    except CremeEntity.DoesNotExist:
                        continue

                    sub_relations = relations.filter(Q(object_entity__id=obj_id))

                    if is_count:
                        y_append(sub_relations.count())
                    else:
                        sub_entities = model_objects_filter(pk__in=sub_relations.values_list('subject_entity__id'))
                        y_append(sub_entities.aggregate(aggregate_col).get(ordinate))

        for i, item in enumerate(y):
            if item is None:
                y[i] = 0

        return (x, y)

    class InstanceBlockConfigItemError(Exception): pass

    def create_instance_block_config_item(self, volatile_field=None, volatile_rtype=None, save=True):
        from reports.blocks import ReportGraphBlock

        if volatile_field:
            assert volatile_rtype is None
            verbose = get_verbose_field_name(self.report.ct.model_class(), volatile_field)
            key = u"%s|%s" % (volatile_field, HFI_FIELD)
        elif volatile_rtype:
            verbose = unicode(volatile_rtype)
            key = u"%s|%s" % (volatile_rtype.id, HFI_RELATION)
        else:
            verbose = ugettext(u'None')
            key = ''

        block_id = InstanceBlockConfigItem.generate_id(ReportGraphBlock, self, key)

        if InstanceBlockConfigItem.objects.filter(block_id=block_id).exists():
            raise self.InstanceBlockConfigItemError(
                        ugettext(u'The instance block for %(graph)s with %(column)s already exists !') % {
                                        'graph':  self,
                                        'column': verbose,
                                    }
                    )

        ibci = InstanceBlockConfigItem(entity=self, block_id=block_id, data=key,
                                       verbose=u"%s - %s" % (self, verbose),
                                      )

        if save:
            ibci.save()

        return ibci


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

#TODO: move to utils ???
def fetch_graph_from_instance_block(instance_block, entity, order='ASC'):
    volatile_column   = instance_block.data

    graph             = instance_block.entity.get_real_entity()
    report            = graph.report
    report_model      = report.ct.model_class()

    model             = entity.__class__
    ct_entity         = entity.entity_type #entity should always be a CremeEntity because graphs can be created only on CremeEntities

    columns = volatile_column.split('|')
    volatile_column, hfi_type = (columns[0], columns[1]) if columns[0] else ('', 0)

    try:
        hfi_type = int(hfi_type)
    except ValueError:
        hfi_type = 0

    x, y = [], []

    if hfi_type == HFI_FIELD:
        try:
            field = report_model._meta.get_field(volatile_column)
        except FieldDoesNotExist:
            pass
        else:
            if field.get_internal_type() == 'ForeignKey' and field.rel.to == model:
                x, y = graph.fetch(extra_q=Q(**{str('%s__pk' % volatile_column): entity.pk}),
                                   order=order
                                  )
    elif hfi_type == HFI_RELATION:
        try:
            rtype = RelationType.objects.get(pk=volatile_column)
        except RelationType.DoesNotExist:
            pass
        else:
            obj_ctypes = rtype.object_ctypes.all()

            if not obj_ctypes or ct_entity in obj_ctypes:
                x, y = graph.fetch(extra_q=Q(relations__type=rtype) & \
                                           Q(relations__object_entity=entity.pk),
                                   order=order
                                  )
    else:
        x, y = graph.fetch(order=order)

    return (x, y)
