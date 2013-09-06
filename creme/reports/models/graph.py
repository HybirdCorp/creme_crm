# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from json import dumps as json_encode
import logging

from django.db.models import (PositiveIntegerField, CharField, BooleanField,
                              ForeignKey, FieldDoesNotExist, Min, Max)
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_lazy as _, pgettext_lazy, ugettext

from creme.creme_core.models import (CremeEntity, RelationType, Relation,
        InstanceBlockConfigItem, CustomField, CustomFieldEnumValue, CustomFieldEnum)
from creme.creme_core.models.header_filter import HFI_RELATION, HFI_FIELD
from creme.creme_core.utils.meta import get_verbose_field_name

from ..report_aggregation_registry import field_aggregation_registry
from .report import Report


logger = logging.getLogger(__name__)

#ReportGraph types
RGT_DAY             = 1
RGT_MONTH           = 2
RGT_YEAR            = 3
RGT_RANGE           = 4
RGT_FK              = 5
RGT_RELATION        = 6
RGT_CUSTOM_DAY      = 11
RGT_CUSTOM_MONTH    = 12
RGT_CUSTOM_YEAR     = 13
RGT_CUSTOM_RANGE    = 14
RGT_CUSTOM_FK       = 15

VERBOSE_REPORT_GRAPH_TYPES = {
    RGT_DAY:            _(u"By days"),
    RGT_MONTH:          _(u"By months"),
    RGT_YEAR:           _(u"By years"),
    RGT_RANGE:          _(u"By X days"),
    RGT_FK:             _(u"By values"),
    RGT_RELATION:       _(u"By values (of related entities)"),
    RGT_CUSTOM_DAY:     _(u"By days"),
    RGT_CUSTOM_MONTH:   _(u"By months"),
    RGT_CUSTOM_YEAR:    _(u"By years"),
    RGT_CUSTOM_RANGE:   _(u"By X days"),
    RGT_CUSTOM_FK:      _(u"By values (of custom choices)"),
}

#TODO: move to creme_core ?
#TODO: use a builder (to reduce the number of temp strings) ?
def listview_url(model, q_filter):
    return '%s?q_filter=%s' % (model.get_lv_absolute_url(), json_encode(q_filter))


class ReportGraph(CremeEntity):
    name     = CharField(pgettext_lazy('reports-graphs', u'Name of the graph'), max_length=100)
    report   = ForeignKey(Report)
    abscissa = CharField(_(u'Abscissa axis'), max_length=100)
    ordinate = CharField(_(u'Ordinate axis'), max_length=100)
    type     = PositiveIntegerField(_(u'Type')) #see RGT_*
    days     = PositiveIntegerField(_(u'Days'), blank=True, null=True)
    is_count = BooleanField(_(u'Make a count instead of aggregate?')) #TODO: 'count' function instead ???

    creation_label = _("Add a report's graph")

    class Meta:
        app_label = 'reports'
        verbose_name = _(u"Report's graph")
        verbose_name_plural = _(u"Reports' graphs")
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "/reports/graph/%s" % self.id

    #def get_edit_absolute_url(self):
        #return "/reports/graph/edit/%s" % self.id

    def get_related_entity(self):
        return self.report

    def fetch(self, extra_q=None, order='ASC'):
        assert order == 'ASC' or order == 'DESC'
        report   = self.report
        ct       = report.ct
        model    = ct.model_class()
        gtype    = self.type
        abscissa = self.abscissa
        ordinate = self.ordinate
        is_count = self.is_count

        if is_count:
            aggregate_col = None

            def y_value(sub_entities):
                return sub_entities.count()

        else:
            ordinate_col, sep, aggregation = ordinate.rpartition('__')
            aggregate_func = field_aggregation_registry.get(aggregation).func

            if ordinate_col.isdigit(): #CustomField
                try:
                    cf = CustomField.objects.get(pk=ordinate_col)
                except CustomField.DoesNotExist: #TODO: test this
                    logger.warn('ReportGraph.fetch: CustomField with id="%s" does not exist', ordinate_col)
                    return [], [] #TODO: notify the user that this graph is deprecated ??

                cf_agg_key = '%s__value' % cf.get_value_class().get_related_name()

                def y_value(sub_entities):
                    return sub_entities.aggregate(cf_agg=aggregate_func(cf_agg_key)).get('cf_agg') or 0

            else: #Regular Field
                aggregate_col = aggregate_func(ordinate_col) #TODO: if field does not exit anymore ??

                def y_value(sub_entities):
                    return sub_entities.aggregate(aggregate_col).get(ordinate) or 0


        entities = model.objects.all()

        if report.filter is not None:
            entities = report.filter.filter(entities)

        if extra_q is not None:
            entities = entities.filter(extra_q)

        entities_filter = entities.filter

        x = []
        y = []
        x_append = x.append
        y_append = y.append

        #TODO: map of functions ??? or objects (see form)
        if gtype == RGT_DAY:
            year_key  = '%s__year' % abscissa
            month_key = '%s__month' % abscissa
            day_key   ='%s__day' % abscissa
            x, y = _get_dates_values(entities, abscissa, y_value, 'day',
                                     qdict_builder=lambda date: {year_key:  date.year,
                                                                 month_key: date.month,
                                                                 day_key:   date.day,
                                                                },
                                     date_format="%d/%m/%Y", order=order,
                                    )
        elif gtype == RGT_MONTH:
            year_key  = '%s__year' % abscissa
            month_key = '%s__month' % abscissa
            x, y = _get_dates_values(entities, abscissa, y_value, 'month',
                                     qdict_builder=lambda date: {year_key:  date.year,
                                                                 month_key: date.month,
                                                                },
                                     date_format="%m/%Y", order=order,
                                    )
        elif gtype == RGT_YEAR:
            year_key  = '%s__year' % abscissa
            x, y = _get_dates_values(entities, abscissa, y_value, 'year',
                                     qdict_builder=lambda date: {year_key: date.year},
                                     date_format="%Y", order=order,
                                    )
        elif gtype == RGT_RANGE:
            date_aggregates = entities.aggregate(min_date=Min(abscissa), max_date=Max(abscissa))
            min_date = date_aggregates['min_date']
            max_date = date_aggregates['max_date']

            if min_date is not None and max_date is not None:
                days = timedelta((self.days or 1) - 1)
                query_cmd = '%s__range' % abscissa

                #TODO: factorise the 2 'while' loops
                if order == 'ASC':
                    while min_date <= max_date:
                        begin = min_date
                        end   = min_date + days
                        x_append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y"))) #TODO: use format from settings ??

                        sub_entities = entities_filter(**{query_cmd: (begin, end)})
                        url = listview_url(model, {query_cmd: [begin.strftime("%Y-%m-%d"),
                                                               end.strftime("%Y-%m-%d"),
                                                              ]
                                                  }
                                          )

                        y_append([y_value(sub_entities), url])

                        min_date = end + timedelta(days=1)
                else:
                    while max_date >= min_date:
                        begin = max_date
                        end   = max_date - days
                        x_append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")))

                        sub_entities = entities_filter(**{query_cmd: (end, begin)})
                        url = listview_url(model, {query_cmd: [end.strftime("%Y-%m-%d"),
                                                               begin.strftime("%Y-%m-%d"),
                                                              ]
                                                  }
                                          )

                        y_append([y_value(sub_entities), url])

                        max_date = end - timedelta(days=1)
        elif gtype == RGT_FK:
            related_instances = model._meta.get_field(abscissa).rel.to.objects.all() #TODO: list (reverse seems useless in most cases)

            if order == 'DESC':
                related_instances = related_instances.reverse()

            for instance in related_instances:
                x_append(unicode(instance))

                kwargs = {abscissa: instance.id}
                y_append([y_value(entities_filter(**kwargs)), listview_url(model, kwargs)])
        if gtype == RGT_CUSTOM_DAY:
            x, y = _get_custom_dates_values(entities, abscissa, y_value, 'day',
                                            qdict_builder=lambda date: {'customfielddatetime__value__year':  date.year,
                                                                        'customfielddatetime__value__month': date.month,
                                                                        'customfielddatetime__value__day':   date.day,
                                                                       },
                                            date_format="%d/%m/%Y", order=order,
                                           )
        elif gtype == RGT_CUSTOM_MONTH:
            x, y = _get_custom_dates_values(entities, abscissa, y_value, 'month',
                                            qdict_builder=lambda date: {'customfielddatetime__value__year':  date.year,
                                                                        'customfielddatetime__value__month': date.month,
                                                                       },
                                            date_format="%m/%Y", order=order,
                                           )
        elif gtype == RGT_CUSTOM_YEAR:
            x, y = _get_custom_dates_values(entities, abscissa, y_value, 'year',
                                            qdict_builder=lambda date: {'customfielddatetime__value__year': date.year},
                                            date_format="%Y", order=order,
                                           )
        elif gtype == RGT_CUSTOM_RANGE:
            try:
                cf = CustomField.objects.get(pk=abscissa)
            except CustomField.DoesNotExist:
                pass #TODO: notify the user that this graph is deprecated ??
            else:
                date_aggregates = entities.aggregate(min_date=Min('customfielddatetime__value'),
                                                     max_date=Max('customfielddatetime__value'),
                                                    ) #TODO: several cf...
                min_date = date_aggregates['min_date']
                max_date = date_aggregates['max_date']

                if min_date is not None and max_date is not None:
                    days = timedelta((self.days or 1) - 1)

                    #TODO: factorise the 2 'while' loops
                    if order == 'ASC':
                        while min_date <= max_date:
                            begin = min_date
                            end   = min_date + days
                            x_append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y"))) #TODO: use format from settings ??

                            sub_entities = entities_filter(customfielddatetime__value__range=(begin, end))
                            url = listview_url(model,
                                               {'customfielddatetime__value__range': [begin.strftime("%Y-%m-%d"),
                                                                                      end.strftime("%Y-%m-%d"),
                                                                                     ],
                                               }
                                              )

                            y_append([y_value(sub_entities), url])

                            min_date = end + timedelta(days=1)
                    else:
                        while max_date >= min_date:
                            begin = max_date
                            end   = max_date - days
                            x_append("%s-%s" % (begin.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y")))

                            sub_entities = entities_filter(customfielddatetime__value__range=(end, begin))
                            url = listview_url(model,
                                               {'customfielddatetime__value__range': [end.strftime("%Y-%m-%d"),
                                                                                      begin.strftime("%Y-%m-%d"),
                                                                                     ],
                                               }
                                              )
                            y_append([y_value(sub_entities), url])

                            max_date = end - timedelta(days=1)
        elif gtype == RGT_CUSTOM_FK: #TODO: factorise with RGT_FK case ??
            try:
                cf = CustomField.objects.get(pk=abscissa)
            except CustomField.DoesNotExist:
                logger.warn('ReportGraph.fetch: CustomField with id="%s" does not exist', abscissa)
                pass #TODO: notify the user that this graph is deprecated ??
            else:
                related_instances = list(CustomFieldEnumValue.objects.filter(custom_field=cf))
                if order == 'DESC':
                    related_instances.reverse()

                for instance in related_instances:
                    x_append(unicode(instance))

                    kwargs = {'customfieldenum__value': instance.id}
                    y_append([y_value(entities_filter(**kwargs)), listview_url(model, kwargs)])
        elif gtype == RGT_RELATION:
            #TODO: Optimize ! (populate real entities)
            #TODO: make listview url for this case
            #      the q_filter {"pk__in": ub_relations.values_list('subject_entity__id')} may create too long urls
            try:
                rt = RelationType.objects.get(pk=abscissa)
            except RelationType.DoesNotExist:
                pass
            else:
                relations = Relation.objects.filter(type=rt, subject_entity__entity_type=ct)
                obj_ids = relations.values_list('object_entity', flat=True).distinct()
                ce_objects_get = CremeEntity.objects.get
                rel_filter = relations.filter

                for obj_id in obj_ids:
                    try:
                        x_append(unicode(ce_objects_get(pk=obj_id).get_real_entity()))
                    except CremeEntity.DoesNotExist:
                        continue

                    subj_ids = rel_filter(object_entity=obj_id).values_list('subject_entity')

                    y_append(y_value(entities_filter(pk__in=subj_ids)))

        return (x, y)

    class InstanceBlockConfigItemError(Exception):
        pass

    def create_instance_block_config_item(self, volatile_field=None, volatile_rtype=None, save=True):
        from creme.reports.blocks import ReportGraphBlock

        if volatile_field: #TODO: unit test
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


def _get_dates_values(entities, abscissa, y_value_func, kind, qdict_builder, date_format, order):
    """
    @param kind 'day', 'month' or 'year'
    @param order 'ASC' or 'DESC'
    @param date_format Format compatible with strftime()
    """
    model = entities.model
    entities_filter = entities.filter
    x = []
    y = []

    for date in entities.dates(abscissa, kind, order):
        qdict = qdict_builder(date)
        x.append(date.strftime(date_format))
        y.append([y_value_func(entities_filter(**qdict)), listview_url(model, qdict)])

    return x, y

def _get_custom_dates_values(entities, abscissa, y_value_func, kind, qdict_builder, date_format, order):
    """
    @param kind 'day', 'month' or 'year'
    @param order 'ASC' or 'DESC'
    @param date_format Format compatible with strftime()
    """
    x = []
    y = []

    try:
        cf = CustomField.objects.get(pk=abscissa)
    except CustomField.DoesNotExist:
        logger.warn('ReportGraph.fetch: CustomField with id="%s" does not exist', abscissa)
        pass #TODO: notify the user that this graph is deprecated ??
    else:
        model = entities.model
        entities_filter = entities.filter

        #TODO: collision with other join on customfielddatetime ???? -> test with quick search when repaired

        #for date in entities.dates('customfielddatetime__value', kind, order):
        for date in entities_filter(customfielddatetime__custom_field=cf).dates('customfielddatetime__value', kind, order):
            qdict = qdict_builder(date)
            qdict['customfielddatetime__custom_field'] = cf.id

            x.append(date.strftime(date_format))
            y.append([y_value_func(entities_filter(**qdict)), listview_url(model, qdict)])

    return x, y

#TODO: move to utils ???
def fetch_graph_from_instance_block(instance_block, entity, order='ASC'):
    volatile_column = instance_block.data
    graph           = instance_block.entity.get_real_entity()
    ct_entity       = entity.entity_type #entity should always be a CremeEntity because graphs can be created only on CremeEntities

    columns = volatile_column.split('|')
    volatile_column, hfi_type = (columns[0], columns[1]) if columns[0] else ('', 0)

    try:
        hfi_type = int(hfi_type)
    except ValueError:
        hfi_type = 0

    x = []
    y = []

    if hfi_type == HFI_FIELD: #TODO: unit test
        try:
            field = graph.report.ct.model_class()._meta.get_field(volatile_column)
        except FieldDoesNotExist:
            pass
        else:
            if field.get_internal_type() == 'ForeignKey' and field.rel.to == entity.__class__: #TODO: use isinstance()
                x, y = graph.fetch(extra_q=Q(**{str('%s__pk' % volatile_column): entity.pk}), #TODO: str() ??
                                   order=order
                                  )
    elif hfi_type == HFI_RELATION: #TODO: unit test
        try:
            rtype = RelationType.objects.get(pk=volatile_column)
        except RelationType.DoesNotExist:
            pass
        else:
            obj_ctypes = rtype.object_ctypes.all()

            if not obj_ctypes or ct_entity in obj_ctypes: #TODO: use RelationType.is_compatible
                x, y = graph.fetch(extra_q=Q(relations__type=rtype,
                                             relations__object_entity=entity.pk,
                                            ),
                                   order=order
                                  )
    else:
        x, y = graph.fetch(order=order)

    return (x, y)
