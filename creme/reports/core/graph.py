# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2014  Hybird
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

from django.db.models import Min, Max, FieldDoesNotExist, Q, ForeignKey
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeEntity, RelationType, Relation, CustomField, CustomFieldEnumValue
#from creme.creme_core.models.header_filter import RFT_RELATION, RFT_FIELD
from creme.creme_core.utils.meta import FieldInfo

from ..constants import *
from ..report_aggregation_registry import field_aggregation_registry


logger = logging.getLogger(__name__)


#TODO: move to creme_core ?
class ListViewURLBuilder(object):
    def __init__(self, model, filter=None):
        self._fmt = model.get_lv_absolute_url() + '?q_filter=%s'

        if filter:
            self._fmt += '&filter=' + filter.id

    def __call__(self, q_filter=None):
        return self._fmt % (json_encode(q_filter) if q_filter is not None else '')


class ReportGraphHandRegistry(object):
    __slots__ = ('_hands', )

    def __init__(self):
        self._hands = {}

    def __call__(self, hand_id):
        assert hand_id not in self._hands, 'ID collision'

        def _aux(cls):
            self._hands[hand_id] = cls
            cls.hand_id = hand_id
            return cls

        return _aux

    def __getitem__(self, i):
        return self._hands[i]

    def __iter__(self):
        return iter(self._hands)

    def get(self, i):
        return self._hands.get(i)


RGRAPH_HANDS_MAP = ReportGraphHandRegistry()


class ReportGraphYCalculator(object):
    def __init__(self):
        self.error = None

    def __call__(self, entities):
        return 0

    @staticmethod
    def build(graph):
        if graph.is_count:
            calculator = RGYCCount()
        else:
            ordinate = graph.ordinate
            ordinate_col, sep, aggregation_name = ordinate.rpartition('__')
            aggregation = field_aggregation_registry.get(aggregation_name) #TODO: manage invalid aggregation ??

            if ordinate_col.isdigit(): #CustomField
                try:
                    calculator = RGYCCustomField(CustomField.objects.get(pk=ordinate_col), aggregation)
                except CustomField.DoesNotExist:
                    calculator = ReportGraphYCalculator()
                    calculator.error = _('the custom field does not exist any more.')
            else: #Regular Field
                try:
                    field = graph.report.ct.model_class()._meta.get_field(ordinate_col) #TODO: method model() in ReportGraph ??
                except FieldDoesNotExist:
                    calculator = ReportGraphYCalculator()
                    calculator.error = _('the field does not exist any more.')
                else:
                    calculator = RGYCField(field, aggregation)

        return calculator

    @property
    def verbose_name(self):
        return '??'


class RGYCCount(ReportGraphYCalculator):
    def __call__(self, entities):
        return entities.count()

    @property
    def verbose_name(self):
        return _('Count')


class RGYCAggregation(ReportGraphYCalculator):
    def __init__(self, aggregation, aggregate_value):
        super(RGYCAggregation, self).__init__()
        self._aggregation = aggregation
        self._aggregate_value = aggregate_value

    def __call__(self, entities):
        return entities.aggregate(rgyc_value_agg=self._aggregate_value).get('rgyc_value_agg') or 0

    def _name(self):
        raise NotImplementedError

    @property
    def verbose_name(self):
        return u'%s - %s' % (self._name(), self._aggregation.title)


class RGYCField(RGYCAggregation):
    def __init__(self, field, aggregation):
        super(RGYCField, self).__init__(aggregation, aggregation.func(field.name))
        self._field = field

    def _name(self):
        return self._field.verbose_name


class RGYCCustomField(RGYCAggregation):
    def __init__(self, cfield, aggregation):
        super(RGYCCustomField, self).__init__(
            aggregation,
            aggregation.func('%s__value' % cfield.get_value_class().get_related_name()),
           )
        self._cfield = cfield

    def _name(self):
        return self._cfield.name


class ReportGraphHand(object):
    "Class that computes abscissa & ordinate values of a ReportGraph"
    verbose_name = 'OVERLOADME'
    hand_id = None #set by ReportGraphHandRegistry decorator

    def __init__(self, graph):
        self._graph = graph
        self._y_calculator = y_calculator = ReportGraphYCalculator.build(graph)
        self.abscissa_error = None
        self.ordinate_error = y_calculator.error

    def _listview_url_builder(self):
        return ListViewURLBuilder(self._graph.report.ct.model_class(), self._graph.report.filter)

    def _fetch(self, entities, order):
        #TODO: Python3.3 version: yield from ()
        return
        yield

    def fetch(self, entities, order):
        """Returns the X & Y values.
        @param entities Queryset of CremeEntities.
        @param order 'ASC' or 'DESC'.
        @return A tuple (X, Y). X is a list of string labels.
                Y is a list of numerics, or of tuple (numeric, URL).
        """
        x_values = []
        y_values = []

        if not self.abscissa_error:
            x_append = x_values.append
            y_append = y_values.append

            for x, y in self._fetch(entities, order):
                x_append(x)
                y_append(y)

        return x_values, y_values

    @property
    def verbose_abscissa(self):
        raise NotImplementedError

    @property
    def verbose_ordinate(self):
        return self._y_calculator.verbose_name


class _RGHRegularField(ReportGraphHand):
    def __init__(self, graph):
        super(_RGHRegularField, self).__init__(graph)

        try:
            field = graph.report.ct.model_class()._meta.get_field(graph.abscissa) #TODO: method model() in ReportGraph ??
        except FieldDoesNotExist:
            field = None
            self.abscissa_error = _('the field does not exist any more.')

        self._field = field

    def _get_dates_values(self, entities, abscissa, kind, qdict_builder, date_format, order):
        """
        @param kind 'day', 'month' or 'year'
        @param order 'ASC' or 'DESC'
        @param date_format Format compatible with strftime()
        """
        build_url = self._listview_url_builder()
        entities_filter = entities.filter
        y_value_func = self._y_calculator

        for date in entities.dates(self._field.name, kind, order):
            qdict = qdict_builder(date)
            yield date.strftime(date_format), [y_value_func(entities_filter(**qdict)), build_url(qdict)]

    @property
    def verbose_abscissa(self):
        field = self._field
        return field.verbose_name if field else '??'


@RGRAPH_HANDS_MAP(RGT_DAY)
class RGHDay(_RGHRegularField):
    verbose_name = _(u"By days")

    def _fetch(self, entities, order):
        abscissa = self._graph.abscissa
        year_key  = '%s__year' % abscissa
        month_key = '%s__month' % abscissa
        day_key   ='%s__day' % abscissa

        return self._get_dates_values(entities, abscissa, 'day',
                                      qdict_builder=lambda date: {year_key:  date.year,
                                                                  month_key: date.month,
                                                                  day_key:   date.day,
                                                                 },
                                      date_format="%d/%m/%Y", order=order,
                                     )


@RGRAPH_HANDS_MAP(RGT_MONTH)
class RGHMonth(_RGHRegularField):
    verbose_name = _(u"By months")

    def _fetch(self, entities, order):
        abscissa = self._graph.abscissa
        year_key  = '%s__year' % abscissa
        month_key = '%s__month' % abscissa

        return self._get_dates_values(entities, abscissa, 'month',
                                      qdict_builder=lambda date: {year_key:  date.year,
                                                                  month_key: date.month,
                                                                 },
                                      date_format="%m/%Y", order=order,
                                     )


@RGRAPH_HANDS_MAP(RGT_YEAR)
class RGHYear(_RGHRegularField):
    verbose_name =_(u"By years")

    def _fetch(self, entities, order):
        abscissa = self._graph.abscissa

        return self._get_dates_values(entities, abscissa, 'year',
                                      qdict_builder=lambda date: {'%s__year' % abscissa: date.year},
                                      date_format="%Y", order=order,
                                     )

#TODO: move to creme_core ??
class DateInterval(object):
    def __init__(self, begin, end, before=None, after=None):
        self.begin = begin
        self.end = end
        self.before = before or begin
        self.after = after or end

    @staticmethod
    def generate(days_duration, min_date, max_date, order):
        days = timedelta(days_duration)

        if order == 'ASC':
            while min_date <= max_date:
                begin = min_date
                end   = min_date + days
                yield DateInterval(begin, end)

                min_date = end + timedelta(days=1)
        else:
            while min_date <= max_date:
                begin = max_date
                end   = max_date - days
                yield DateInterval(begin, end, end, begin)

                max_date = end - timedelta(days=1)


@RGRAPH_HANDS_MAP(RGT_RANGE)
class RGHRange(_RGHRegularField):
    verbose_name = _(u"By X days")

    def _fetch(self, entities, order):
        graph = self._graph
        abscissa = graph.abscissa

        date_aggregates = entities.aggregate(min_date=Min(abscissa), max_date=Max(abscissa))
        min_date = date_aggregates['min_date']
        max_date = date_aggregates['max_date']

        if min_date is not None and max_date is not None:
            build_url = self._listview_url_builder()
            query_cmd = '%s__range' % abscissa
            entities_filter = entities.filter
            y_value_func = self._y_calculator

            for interval in DateInterval.generate((graph.days or 1) - 1, min_date, max_date, order):
                before = interval.before
                after  = interval.after
                sub_entities = entities_filter(**{query_cmd: (before, after)})

                yield ('%s-%s' % (interval.begin.strftime("%d/%m/%Y"), #TODO: use format from settings ??
                                  interval.end.strftime("%d/%m/%Y"),
                                 ),
                       [y_value_func(sub_entities),
                        build_url({query_cmd: [before.strftime("%Y-%m-%d"),
                                               after.strftime("%Y-%m-%d"),
                                              ]
                                  }
                               )
                       ],
                      )


@RGRAPH_HANDS_MAP(RGT_FK)
class RGHForeignKey(_RGHRegularField):
    verbose_name = _(u"By values")

    def _fetch(self, entities, order):
        abscissa = self._graph.abscissa
        build_url = self._listview_url_builder()
        entities_filter = entities.filter
        y_value_func = self._y_calculator

        related_instances = list(entities.model._meta.get_field(abscissa).rel.to.objects.all())
        if order == 'DESC':
            related_instances.reverse()

        for instance in related_instances:
            kwargs = {abscissa: instance.id}
            yield unicode(instance), [y_value_func(entities_filter(**kwargs)), build_url(kwargs)]


@RGRAPH_HANDS_MAP(RGT_RELATION)
class RGHRelation(ReportGraphHand):
    verbose_name = _(u"By values (of related entities)")

    def __init__(self, graph):
        super(RGHRelation, self).__init__(graph)

        try:
            rtype = RelationType.objects.get(pk=self._graph.abscissa)
        except RelationType.DoesNotExist:
            rtype = None
            self.abscissa_error = _('the relationship type does not exist any more.')

        self._rtype = rtype

    def _fetch(self, entities, order):
        #TODO: Optimize ! (populate real entities)
        #TODO: sort alpbabetically (with header_filter_search_field ? Queryset is not paginated so we can sort the "list") ?
        #TODO: make listview url for this case
        build_url = self._listview_url_builder()
        relations = Relation.objects.filter(type=self._rtype, subject_entity__entity_type=self._graph.report.ct)
        rel_filter = relations.filter
        ce_objects_get = CremeEntity.objects.get
        entities_filter = entities.filter
        y_value_func = self._y_calculator

        for obj_id in relations.values_list('object_entity', flat=True).distinct():
            subj_ids = rel_filter(object_entity=obj_id).values_list('subject_entity')

            yield (unicode(ce_objects_get(pk=obj_id).get_real_entity()),
                   [y_value_func(entities_filter(pk__in=subj_ids)), build_url({'pk__in': [e[0] for e in subj_ids]})],
                  )

    @property
    def verbose_abscissa(self):
        rtype = self._rtype
        return rtype.predicate if rtype else '??'


class _RGHCustomField(ReportGraphHand):
    def __init__(self, graph):
        super(_RGHCustomField, self).__init__(graph)
        abscissa = self._graph.abscissa

        try:
            cfield = CustomField.objects.get(pk=abscissa)
        except CustomField.DoesNotExist:
            cfield = None
            self.abscissa_error = _('the custom field does not exist any more.')

        self._cfield = cfield

    def _get_custom_dates_values(self, entities, abscissa, kind, qdict_builder, date_format, order):
        """
        @param kind 'day', 'month' or 'year'
        @param order 'ASC' or 'DESC'
        @param date_format Format compatible with strftime()
        """
        cfield = self._cfield
        build_url = self._listview_url_builder()
        entities_filter = entities.filter
        y_value_func = self._y_calculator

        for date in entities_filter(customfielddatetime__custom_field=cfield) \
                                   .dates('customfielddatetime__value', kind, order):
            qdict = qdict_builder(date)
            qdict['customfielddatetime__custom_field'] = cfield.id

            yield date.strftime(date_format), [y_value_func(entities_filter(**qdict)), build_url(qdict)]

    @property
    def verbose_abscissa(self):
        cfield = self._cfield
        return cfield.name if cfield else '??'


@RGRAPH_HANDS_MAP(RGT_CUSTOM_DAY)
class RGHCustomDay(_RGHCustomField):
    verbose_name = _(u"By days")

    def _fetch(self, entities, order):
        return self._get_custom_dates_values(entities, self._graph.abscissa, 'day',
                                             qdict_builder=lambda date: {'customfielddatetime__value__year':  date.year,
                                                                         'customfielddatetime__value__month': date.month,
                                                                         'customfielddatetime__value__day':   date.day,
                                                                        },
                                             date_format="%d/%m/%Y", order=order,
                                            )


@RGRAPH_HANDS_MAP(RGT_CUSTOM_MONTH)
class RGHCustomMonth(_RGHCustomField):
    verbose_name = _(u"By months")

    def _fetch(self, entities, order):
        return self._get_custom_dates_values(entities, self._graph.abscissa, 'month',
                                             qdict_builder=lambda date: {'customfielddatetime__value__year':  date.year,
                                                                         'customfielddatetime__value__month': date.month,
                                                                        },
                                             date_format="%m/%Y", order=order,
                                            )


@RGRAPH_HANDS_MAP(RGT_CUSTOM_YEAR)
class RGHCustomYear(_RGHCustomField):
    verbose_name = _(u"By years")

    def _fetch(self, entities, order):
        return self._get_custom_dates_values(entities, self._graph.abscissa, 'year',
                                             qdict_builder=lambda date: {'customfielddatetime__value__year': date.year},
                                             date_format="%Y", order=order,
                                            )


@RGRAPH_HANDS_MAP(RGT_CUSTOM_RANGE)
class RGHCustomRange(_RGHCustomField):
    verbose_name = _(u"By X days")

    def _fetch(self, entities, order):
        cfield = self._cfield
        entities_filter = entities.filter
        date_aggregates = entities_filter(customfielddatetime__custom_field=cfield) \
                                         .aggregate(min_date=Min('customfielddatetime__value'),
                                                    max_date=Max('customfielddatetime__value'),
                                                   )
        min_date = date_aggregates['min_date']
        max_date = date_aggregates['max_date']

        if min_date is not None and max_date is not None:
            y_value_func = self._y_calculator
            build_url = self._listview_url_builder()

            for interval in DateInterval.generate((self._graph.days or 1) - 1, min_date, max_date, order):
                before = interval.before
                after  = interval.after
                sub_entities = entities_filter(customfielddatetime__custom_field=cfield,
                                               customfielddatetime__value__range=(before, after),
                                              )

                yield ('%s-%s' % (interval.begin.strftime("%d/%m/%Y"), #TODO: use format from settings ??
                                  interval.end.strftime("%d/%m/%Y"),
                                 ),
                       [y_value_func(sub_entities),
                        build_url({'customfielddatetime__custom_field': cfield.id,
                                   'customfielddatetime__value__range': [before.strftime("%Y-%m-%d"),
                                                                         after.strftime("%Y-%m-%d"),
                                                                        ],
                                  }
                                 )
                       ]
                      )


@RGRAPH_HANDS_MAP(RGT_CUSTOM_FK)
class RGHCustomFK(_RGHCustomField):
    verbose_name = _(u"By values (of custom choices)")

    def _fetch(self, entities, order):
        entities_filter = entities.filter
        y_value_func = self._y_calculator
        build_url = self._listview_url_builder()
        related_instances = list(CustomFieldEnumValue.objects.filter(custom_field=self._cfield))

        if order == 'DESC':
            related_instances.reverse()

        for instance in related_instances:
            kwargs = {'customfieldenum__value': instance.id}

            yield unicode(instance), [y_value_func(entities_filter(**kwargs)), build_url(kwargs)]


#def fetch_graph_from_instance_block(instance_block, entity, order='ASC'):
    #volatile_column = instance_block.data
    #graph           = instance_block.entity.get_real_entity()
    #ct_entity       = entity.entity_type #entity should always be a CremeEntity because graphs can be created only on CremeEntities

    #columns = volatile_column.split('|')
    #volatile_column, hfi_type = (columns[0], columns[1]) if columns[0] else ('', 0)

    #try:
        #hfi_type = int(hfi_type)
    #except ValueError:
        #hfi_type = 0

    #x = []
    #y = []

    #if hfi_type == RFT_FIELD:
        #try:
            #field = graph.report.ct.model_class()._meta.get_field(volatile_column)
        #except FieldDoesNotExist:
            #pass
        #else:
            #if field.get_internal_type() == 'ForeignKey' and field.rel.to == entity.__class__: #todo: use isinstance()
                #x, y = graph.fetch(extra_q=Q(**{str('%s__pk' % volatile_column): entity.pk}), #todo: str() ??
                                   #order=order
                                  #)
    #elif hfi_type == RFT_RELATION:
        #try:
            #rtype = RelationType.objects.get(pk=volatile_column)
        #except RelationType.DoesNotExist:
            #pass
        #else:
            #obj_ctypes = rtype.object_ctypes.all()

            #if not obj_ctypes or ct_entity in obj_ctypes: #todo: use RelationType.is_compatible
                #x, y = graph.fetch(extra_q=Q(relations__type=rtype,
                                             #relations__object_entity=entity.pk,
                                            #),
                                   #order=order
                                  #)
    #else:
        #x, y = graph.fetch(order=order)

    #return (x, y)

#TODO: we use a map/registry of GraphFetcher classes, and use it in get_fetcher_from_instance_block()
       #and in ReportGraph form to build choices.
class GraphFetcher(object):
    """A graph fetcher can fetch the result of a given ReportGraph, with or without
    a volatile link.
    It stores the verbose name of this link (for UI), and an error if the link data
    were invalid.
    """
    def __init__(self, graph):
        self.graph = graph
        self.error = None
        self.verbose_volatile_column = pgettext_lazy('reports-volatile_choice', u'None')

    def fetch(self, order='ASC'):
        return self.graph.fetch(order=order)

    def _aux_fetch_4_entity(self, entity, order):
        "To be overload in child classes"
        return self.fetch(order=order)

    def fetch_4_entity(self, entity, order='ASC'):
        return ([], []) if self.error else self._aux_fetch_4_entity(entity, order)

    @property
    def verbose_name(self):
        return u"%s - %s" % (self.graph, self.verbose_volatile_column)


class RegularFieldLinkedGraphFetcher(GraphFetcher):
    def __init__(self, field_name, *args, **kwargs):
        super(RegularFieldLinkedGraphFetcher, self).__init__(*args, **kwargs)
        model = self.graph.report.ct.model_class()
        self.field_name = None
        self.verbose_volatile_column = '??'

        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            logger.warn(u'Instance block: invalid field %s.%s in block config.',
                        model.__name__, field_name,
                       )
            self.error = _('The field is invalid.')
        else:
            if isinstance(field, ForeignKey):
                self.verbose_volatile_column = field.verbose_name
                self._field_name = field_name
                self._volatile_model = field.rel.to
            else:
                logger.warn('Instance block: field %s.%s in block config is not a FK.',
                            model.__name__, field_name,
                           )
                self.error = _('The field is invalid (not a foreign key).')

    def _aux_fetch_4_entity(self, entity, order):
        return self.graph.fetch(extra_q=Q(**{self._field_name: entity.pk}), order=order) \
               if isinstance(entity, self._volatile_model) else ([], [])

    @staticmethod
    def validate_fieldname(graph, field_name):
        try:
            field_info = FieldInfo(graph.report.ct.model_class(), field_name)
        except FieldDoesNotExist:
            return 'invalid field "%s"' % field_name

        if len(field_info) > 1:
            return 'field "%s" with deep > 1' % field_name

        field = field_info[0]

        if not (isinstance(field, ForeignKey) and issubclass(field.rel.to, CremeEntity)):
            return 'field "%s" is not a ForeignKey to CremeEntity' % field_name


class RelationLinkedGraphFetcher(GraphFetcher):
    def __init__(self, rtype_id, *args, **kwargs):
        super(RelationLinkedGraphFetcher, self).__init__(*args, **kwargs)
        try:
            rtype = RelationType.objects.get(pk=rtype_id)
        except RelationType.DoesNotExist:
            logger.warn('Instance block: invalid RelationType "%s" in block config.',
                        rtype_id,
                       )
            self.error = _('The relationship type is invalid.')
            self.verbose_volatile_column = '??'
        else:
            self.verbose_volatile_column = unicode(rtype)
            self._rtype = rtype

    def _aux_fetch_4_entity(self, entity, order):
        return self.graph.fetch(extra_q=Q(relations__type=self._rtype,
                                          relations__object_entity=entity.pk,
                                         ),
                                order=order,
                               )
