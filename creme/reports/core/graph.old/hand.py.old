################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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

import logging
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from django.db import connection
from django.db.models import Max, Min, Q, QuerySet
from django.utils.formats import get_format
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.enumerable import enumerable_registry
from creme.creme_core.models import CustomFieldEnumValue, Relation
from creme.creme_core.models.fields import ColorField
from creme.reports.constants import AbscissaGroup
from creme.reports.utils import sparsezip

from .aggregator import AGGREGATORS_MAP, ReportGraphAggregator

if TYPE_CHECKING:
    from creme.reports.models import AbstractReportGraph

logger = logging.getLogger(__name__)


def _physical_field_name(table_name, field_name) -> str:
    quote_name = connection.ops.quote_name
    return f'{quote_name(table_name)}.{quote_name(field_name)}'


def _db_grouping_format() -> str:
    vendor = connection.vendor
    if vendor == 'sqlite':
        return "cast((julianday(%s) - julianday(%s)) / %s as int)"

    if vendor == 'mysql':
        return "floor((to_days(%s) - to_days(%s)) / %s)"

    if vendor == 'postgresql':
        return "((%s::date - %s::date) / %s)"

    raise RuntimeError(f'Unsupported vendor: {vendor}')


def _generate_date_format(*, year=False, month=False, day=False):
    """Generate a reduced date format (strftime format) derived from the
    configured DATE_INPUT_FORMATS, using only the wanted information.
    """
    find_fmt = get_format('DATE_INPUT_FORMATS')[0].find

    def find_option(*options):
        for option in options:
            index = find_fmt(option)
            if index != -1:
                return index, option

        return 0, options[0]

    parts = []
    if year:
        parts.append(find_option('%Y', '%y'))
    if month:
        parts.append(find_option('%m'))  # XXX: %b ? %B ?
    if day:
        parts.append(find_option('%d'))
    parts.sort(key=lambda t: t[0])

    separator = find_option('/', '-', '.', ' ')[1]

    return separator.join(t[1] for t in parts)


# HACK: <.replace('%', '%%')> was done by
#  <django.db.backends.mysql.schema.DatabaseSchemaEditor.quote_value()> in django 4.2-,
#  but not in django 5.0. This is probably not the best way to do it;
#  if you have the answer you're welcome.
def _get_value_quoter():
    schema_editor = connection.schema_editor()

    if connection.vendor == 'mysql':
        def quote_value(x):
            return schema_editor.quote_value(x.replace('%', '%%'))
    else:
        def quote_value(x):
            return schema_editor.quote_value(x)

    return quote_value


class ReportGraphHand:
    "Class that computes abscissa & ordinate values of a ReportGraph."
    verbose_name: str = 'OVERRIDE_ME'
    hand_id: int  # Set by ReportGraphHandRegistry decorator

    def __init__(self, graph: AbstractReportGraph):
        self._graph = graph
        self._y_calculator = y_calculator = AGGREGATORS_MAP[graph]
        self.abscissa_error: str | None = None
        self.ordinate_error: str | None = y_calculator.error

    def _listview_url_builder(self, extra_q: Q | None = None):
        from .lv_url import ListViewURLBuilder

        graph = self._graph
        return ListViewURLBuilder(
            model=graph.model,
            filter=graph.linked_report.filter,
            common_q=extra_q,
        )

    def _fetch(self,
               *,
               entities: QuerySet,
               order: str,
               user,
               extra_q: Q | None,
               ) -> Iterator[tuple[str, Any]]:
        yield from ()

    def fetch(self,
              entities: QuerySet,
              order: str,
              user,
              extra_q: Q | None = None,
              ) -> tuple[list[str], list]:
        """Returns the X & Y values.
        @param entities: Queryset of CremeEntities.
        @param order: 'ASC' or 'DESC'.
        @param extra_q: instance of Q, or None ; applied to narrow <entities>.
        @return A tuple (X, Y). X is a list of string labels.
                Y is a list of numerics, or of tuple (numeric, URL).
        """
        x_values: list[str] = []
        y_values: list = []

        if extra_q is not None:
            entities = entities.filter(extra_q)

        if not entities.exists():
            return x_values, y_values

        if not self.abscissa_error:
            x_append = x_values.append
            y_append = y_values.append

            for x, y in self._fetch(
                entities=entities, order=order, user=user, extra_q=extra_q,
            ):
                x_append(x)
                y_append(y)

        return x_values, y_values

    # TODO: deprecate & replace by a property @cell ??
    @property
    def verbose_abscissa(self) -> str:
        raise NotImplementedError

    @property
    def ordinate(self) -> ReportGraphAggregator:
        return self._y_calculator

    # TODO: The 'group by' query could be extracted into a common Manager
    def _aggregate_by_key(self, entities, key, order):
        y_calculator = self._y_calculator
        aggregates = (
            entities.extra({'key': key})
                    .values('key')
                    .order_by('key' if order == 'ASC' else '-key')
                    .filter(y_calculator.annotate_extra_q)
                    .annotate(value=y_calculator.annotate())
                    .values_list('key', 'value')
        )

        # print('query:', aggregates.query, '\n')
        # print('results:', aggregates)

        return aggregates

    def fetch_colormap(self, user) -> dict:
        return {}


class ReportGraphHandRegistry:
    __slots__ = ('_hands', )

    def __init__(self) -> None:
        self._hands: dict[int, type[ReportGraphHand]] = {}

    def __call__(self, hand_id: int):
        assert hand_id not in self._hands, 'ID collision'

        def _aux(cls: type[ReportGraphHand]):
            self._hands[hand_id] = cls
            cls.hand_id = hand_id
            return cls

        return _aux

    def __getitem__(self, i: int) -> type[ReportGraphHand]:
        return self._hands[i]

    def __iter__(self) -> Iterator[int]:
        return iter(self._hands)

    def get(self, i: int) -> type[ReportGraphHand] | None:
        return self._hands.get(i)


RGRAPH_HANDS_MAP = ReportGraphHandRegistry()


class _RGHRegularField(ReportGraphHand):
    def __init__(self, graph):
        super().__init__(graph)

        cell = graph.abscissa_info.cell
        if cell is None:
            field = None
            self.abscissa_error = _('the field does not exist any more.')
        else:
            field = cell.field_info[0]

            if (
                graph.linked_report
                     ._fields_configs
                     .get_for_model(graph.model)
                     .is_field_hidden(field)
            ):
                self.abscissa_error = _('this field should be hidden.')

        self._field = field

# Commented on Nov 21, 2014 when refactoring this method doing a manual 'group by'
# to the _get_dates_values() below using a real sql 'group by'
#    def _get_dates_values(self, entities, abscissa, kind, qdict_builder, date_format, order):
#        """
#        @param kind 'day', 'month' or 'year'
#        @param order 'ASC' or 'DESC'
#        @param date_format Format compatible with strftime()
#        """
#        build_url = self._listview_url_builder()
#        entities_filter = entities.filter
#        y_value_func = self._y_calculator
#
#        for date in entities.dates(self._field.name, kind, order):
#            qdict = qdict_builder(date)
#            yield (date.strftime(date_format),
#                  [y_value_func(entities_filter(**qdict)), build_url(qdict)])

    def _aggregate_dates_by_key(self, entities, abscissa, key, order):
        x_value_filter = {f'{abscissa}__isnull': True}
        aggregates = self._aggregate_by_key(entities, key, order).exclude(**x_value_filter)
        return aggregates

    def _get_dates_values(self, *,
                          entities, abscissa, kind, qdict_builder,
                          date_format, order, extra_q,
                          ):
        """
        @param kind: 'day', 'month' or 'year'.
        @param order: 'ASC' or 'DESC'.
        @param date_format: Format compatible with strftime().
        """
        build_url = self._listview_url_builder(extra_q=extra_q)

        field_name = _physical_field_name(self._field.model._meta.db_table, abscissa)
        x_sql, x_params = connection.ops.date_trunc_sql(
            lookup_type=kind, sql=field_name, params=(),
        )
        # schema_editor = connection.schema_editor()
        # x_value_key = x_sql % tuple(schema_editor.quote_value(p) for p in x_params)
        quote_value = _get_value_quoter()
        x_value_key = x_sql % tuple(quote_value(p) for p in x_params)

        for key, value in self._aggregate_dates_by_key(entities, abscissa, x_value_key, order):
            date = key

            # TODO: When using extras/sql functions on dates and sqlite,
            #       the ORM returns strings instead of datetimes
            # This can probably be fixed/improved when we migrate to Django 1.8,
            # using custom annotation operators.
            if connection.vendor == 'sqlite' and isinstance(key, str):
                # NB: it seems the string format has changed in django1.6
                date = datetime.strptime(key, '%Y-%m-%d')

            qdict = qdict_builder(date)
            yield date.strftime(date_format), [value or 0, build_url(qdict)]

    @property
    def verbose_abscissa(self):
        field = self._field
        return field.verbose_name if field else '??'


@RGRAPH_HANDS_MAP(AbscissaGroup.DAY)
class RGHDay(_RGHRegularField):
    verbose_name = _('By days')

    def _fetch(self, *, entities, order, user, extra_q):
        abscissa = self._field.name
        year_key  = f'{abscissa}__year'
        month_key = f'{abscissa}__month'
        day_key   = f'{abscissa}__day'

        return self._get_dates_values(
            entities=entities,
            abscissa=abscissa, kind='day',
            qdict_builder=lambda date: {
                year_key:  date.year,
                month_key: date.month,
                day_key:   date.day,
            },
            date_format=_generate_date_format(year=True, month=True, day=True),
            order=order,
            extra_q=extra_q,
        )


@RGRAPH_HANDS_MAP(AbscissaGroup.MONTH)
class RGHMonth(_RGHRegularField):
    verbose_name = _('By months')

    def _fetch(self, *, entities, order, user, extra_q):
        abscissa = self._field.name
        year_key  = f'{abscissa}__year'
        month_key = f'{abscissa}__month'

        return self._get_dates_values(
            entities=entities,
            abscissa=abscissa, kind='month',
            qdict_builder=lambda date: {
                year_key:  date.year,
                month_key: date.month,
            },
            date_format=_generate_date_format(year=True, month=True),
            order=order,
            extra_q=extra_q,
        )


@RGRAPH_HANDS_MAP(AbscissaGroup.YEAR)
class RGHYear(_RGHRegularField):
    verbose_name = _('By years')

    def _fetch(self, *, entities, order, user, extra_q):
        abscissa = self._field.name

        return self._get_dates_values(
            entities=entities,
            abscissa=abscissa, kind='year',
            qdict_builder=lambda date: {f'{abscissa}__year': date.year},
            date_format=_generate_date_format(year=True),
            order=order,
            extra_q=extra_q,
        )


# TODO: move to creme_core ??
class DateInterval:
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


class _DateRangeMixin:
    @staticmethod
    def get_days(graph):
        try:
            days = int(graph.abscissa_info.parameter)
        except (TypeError, ValueError) as e:
            logger.warning('Invalid report graph days parameter "%s"', e)
            days = 1

        return days


@RGRAPH_HANDS_MAP(AbscissaGroup.RANGE)
class RGHRange(_DateRangeMixin, _RGHRegularField):
    verbose_name = _('By X days')

    def __init__(self, graph):
        super().__init__(graph)

        self._fetch_method = self._fetch_with_group_by
        vendor = connection.vendor
        if vendor not in {'sqlite', 'mysql', 'postgresql'}:
            logger.warning(
                'Report graph data optimizations not available with DB vendor "%s",'
                ' reverting to slower fallback method.',
                vendor,
            )
            self._fetch_method = self._fetch_fallback

        self._days = self.get_days(graph)

    def _fetch(self, *, entities, order, user, extra_q):
        return self._fetch_method(entities, order, extra_q)

    def _fetch_with_group_by(self, entities, order, extra_q):
        abscissa = self._field.name

        # TODO: When migrating to Django 1.8 (with its support of expressions and sql functions)
        #       these queries can be refactored and get improved performance by pushing part of
        #       the group key computation in the min/max aggregates query (converting the min/max
        #       date to a pivot key). Right now, the value key is a difference with effectively a
        #       constant pivot key, and we could help the DB by giving it the constant value
        #       instead of the computation. It is doable now but is too much of a hack until using
        #       Django 1.8. Reusing the key alias in the 'group by' clause instead of repeating
        #       the complete value as the ORM currently generates could be a possibility as well.
        date_aggregates = entities.aggregate(min_date=Min(abscissa), max_date=Max(abscissa))
        min_date = date_aggregates['min_date']
        max_date = date_aggregates['max_date']

        if min_date is not None and max_date is not None:
            build_url = self._listview_url_builder(extra_q=extra_q)
            query_cmd = f'{abscissa}__range'
            days = self._days

            field_name = _physical_field_name(self._field.model._meta.db_table, abscissa)

            # The aggregate keys are computed by grouping the difference, in
            # days, between the date and the pivot, into buckets of X days & the
            # pivot key is the first value in the ordered set of data.
            x_value_format = _db_grouping_format()
            x_value_key = (
                x_value_format % (field_name, min_date.strftime("'%Y-%m-%d'"), days)
                if order == 'ASC' else
                x_value_format % (max_date.strftime("'%Y-%m-%d'"), field_name, days)
            )

            intervals = DateInterval.generate(days - 1, min_date, max_date, order)
            aggregates = self._aggregate_dates_by_key(entities, abscissa, x_value_key, 'ASC')

            label_fmt = _generate_date_format(year=True, month=True, day=True)
            # TODO: unicode char never used as separator instead?
            label_sep = '-' if '-' not in label_fmt else '/'

            # Fill missing aggregate values and zip them with the date intervals
            for interval, value in sparsezip(intervals, aggregates, 0):
                range_label = '{}{}{}'.format(
                    interval.begin.strftime(label_fmt),
                    label_sep,
                    interval.end.strftime(label_fmt),
                )
                url = build_url({
                    query_cmd: [interval.before, interval.after],
                })

                yield range_label, [value, url]

    def _fetch_fallback(self, entities, order, extra_q):
        """Aggregate values with 'manual group by' by iterating over group
        values and executing an aggregate query per group.
        """
        graph = self._graph
        abscissa = graph.abscissa

        date_aggregates = entities.aggregate(min_date=Min(abscissa), max_date=Max(abscissa))
        min_date = date_aggregates['min_date']
        max_date = date_aggregates['max_date']

        if min_date is not None and max_date is not None:
            build_url = self._listview_url_builder(extra_q=extra_q)
            query_cmd = f'{abscissa}__range'
            entities_filter = entities.filter
            y_value_func = self._y_calculator.aggregate

            label_fmt = _generate_date_format(year=True, month=True, day=True)
            label_sep = '-' if '-' not in label_fmt else '/'

            for interval in DateInterval.generate(
                (graph.days or 1) - 1, min_date, max_date, order,
            ):
                before = interval.before
                after  = interval.after
                sub_entities = entities_filter(**{query_cmd: (before, after)})

                yield (
                    '{}{}{}'.format(
                        interval.begin.strftime(label_fmt),
                        label_sep,
                        interval.end.strftime(label_fmt),
                    ),
                    [
                        y_value_func(sub_entities),
                        build_url({
                            query_cmd: [before, after],
                        }),
                    ],
                )


@RGRAPH_HANDS_MAP(AbscissaGroup.FK)
class RGHForeignKey(_RGHRegularField):
    verbose_name = _('By values')

    def __init__(self, graph):
        super().__init__(graph=graph)
        enumerator = None
        field = self._field

        if field is not None:
            try:
                # TODO: pass the registry as argument
                enumerator = enumerable_registry.enumerator_by_field(field)
            except ValueError:
                self.abscissa_error = _('this field cannot be used as abscissa.')

        self._abscissa_enumerator = enumerator

    def _fetch(self, *, entities, order, user, extra_q):
        abscissa = self._field.name
        build_url = self._listview_url_builder(extra_q=extra_q)
        entities_filter = entities.filter
        y_value_func = self._y_calculator.aggregate
        choices = self._abscissa_enumerator.choices(user=user)

        if order == 'DESC':
            choices.reverse()

        for choice in choices:
            kwargs = {abscissa: choice['value']}
            yield (
                choice['label'],
                [
                    y_value_func(entities_filter(**kwargs)),
                    build_url(kwargs),
                ],
            )

    def model_has_color(self, model):
        try:
            color_field = model._meta.get_field('color')
        except Exception:
            return False

        return isinstance(color_field, ColorField)

    def fetch_colormap(self, user) -> dict:
        fk_model = self._field.related_model

        if not self.model_has_color(fk_model):
            return {}

        choices = self._abscissa_enumerator.choices(user=user)
        fk_objects = {
            e.pk: e for e in fk_model.objects.filter(
                pk__in=[c['value'] for c in choices]
            )
        }

        return {
            c['label']: f"#{fk_objects[c['value']].color}"
            for c in choices
        }


@RGRAPH_HANDS_MAP(AbscissaGroup.CHOICES)
class RGHChoices(_RGHRegularField):
    verbose_name = _('By values')  # TODO: "not configurable"?

    def __init__(self, graph):
        super().__init__(graph=graph)

        if self._field.choices is None:
            self.abscissa_error = _('this field cannot be used as abscissa.')

    def _fetch(self, *, entities, order, user, extra_q):
        abscissa = self._field.name
        build_url = self._listview_url_builder(extra_q=extra_q)
        entities_filter = entities.filter
        y_value_func = self._y_calculator.aggregate
        choices = self._field.choices

        if order == 'DESC':
            choices.reverse()

        for value, label in choices:
            kwargs = {abscissa: value}
            yield (
                label,
                [
                    y_value_func(entities_filter(**kwargs)),
                    build_url(kwargs),
                ],
            )


@RGRAPH_HANDS_MAP(AbscissaGroup.RELATION)
class RGHRelation(ReportGraphHand):
    verbose_name = _('By values (of related entities)')

    def __init__(self, graph):
        super().__init__(graph)

        cell = graph.abscissa_info.cell
        if cell is None:
            rtype = None
            self.abscissa_error = _('the relationship type does not exist any more.')
        else:
            rtype = cell.relation_type

            if not rtype.enabled:
                self.abscissa_error = _('the relationship type is disabled.')

        self._rtype = rtype

    def _fetch(self, *, entities, order, user, extra_q):
        rtype_id = self._rtype.id
        build_url = self._listview_url_builder(extra_q=extra_q)
        entities_filter = entities.filter
        y_value_func = self._y_calculator.aggregate

        # NB: we assume the field "header_filter_search_field" is up-to-date
        #     (it should be in the absolute, but it's not the responsibility of this code)
        # TODO: limit + warning message (in UI) when the limit is reached?
        for obj_id, obj_str in Relation.objects.filter(
            type_id=rtype_id, subject_entity__entity_type=self._graph.linked_report.ct,
        ).values_list(
            'object_entity_id',
            'object_entity__header_filter_search_field',
        ).order_by('object_entity__header_filter_search_field').distinct():
            q_dict = {
                'relations__type_id': rtype_id,
                'relations__object_entity_id': obj_id,
            }

            yield (obj_str, [y_value_func(entities_filter(**q_dict)), build_url(q_dict)])

    @property
    def verbose_abscissa(self):
        rtype = self._rtype
        return rtype.predicate if rtype else '??'


class _RGHCustomField(ReportGraphHand):
    def __init__(self, graph):
        super().__init__(graph)

        cell = graph.abscissa_info.cell
        if cell is None:
            cfield = None
            self.abscissa_error = _('the custom field does not exist any more.')
        else:
            cfield = cell.custom_field

            if cfield.is_deleted:
                self.abscissa_error = _('the custom field is deleted.')

        self._cfield = cfield

# Commented on Nov 21, 2014 when refactoring this method doing a manual 'group by' to the
# _get_custom_dates_values() below using a real sql 'group by'
# def _get_custom_dates_values(self, entities, abscissa, kind, qdict_builder, date_format, order):
#        """
#        @param kind 'day', 'month' or 'year'
#        @param order 'ASC' or 'DESC'
#        @param date_format Format compatible with strftime()
#        """
#        cfield = self._cfield
#        build_url = self._listview_url_builder()
#        entities_filter = entities.filter
#        y_value_func = self._y_calculator
#
#        for date in entities_filter(customfielddatetime__custom_field=cfield) \
#                                   .dates('customfielddatetime__value', kind, order):
#            qdict = qdict_builder(date)
#            qdict['customfielddatetime__custom_field'] = cfield.id
#
#            yield (date.strftime(date_format),
#                 [y_value_func(entities_filter(**qdict)), build_url(qdict)])

    # TODO: This is almost identical to _RGHRegularField._get_dates_values
    #       (differences here - 1: there is no need to exclude null values
    #       2: the entities have an additional filter,
    #       3: the qdicts have an additional value) and could be factored together
    def _get_custom_dates_values(self, *,
                                 entities, kind, qdict_builder, date_format, order, extra_q,
                                 ):
        """
        @param kind: 'day', 'month' or 'year'.
        @param order: 'ASC' or 'DESC'.
        @param date_format: Format compatible with strftime().
        """
        cfield = self._cfield
        value_meta = cfield.value_class._meta
        cfield_q_key = f"{value_meta.get_field('entity').remote_field.name}__custom_field"
        build_url = self._listview_url_builder(extra_q=extra_q)

        entities = entities.filter(**{cfield_q_key: cfield})

        field_name = _physical_field_name(value_meta.db_table, 'value')
        # TODO: factorise
        x_sql, x_params = connection.ops.date_trunc_sql(
            lookup_type=kind, sql=field_name, params=(),
        )
        # schema_editor = connection.schema_editor()
        # x_value_key = x_sql % tuple(schema_editor.quote_value(p) for p in x_params)
        quote_value = _get_value_quoter()
        x_value_key = x_sql % tuple(quote_value(p) for p in x_params)

        for key, value in self._aggregate_by_key(entities, x_value_key, order):
            date = key

            # TODO: When using extras/sql functions on dates and sqlite,
            #       the ORM returns strings instead of datetimes
            #       This can probably be fixed/improved when we migrate to Django 1.8,
            #       using custom annotation operators.
            if connection.vendor == 'sqlite' and isinstance(key, str):
                date = datetime.strptime(key, '%Y-%m-%d')

            qdict = qdict_builder(date)
            qdict[cfield_q_key] = cfield.id

            yield date.strftime(date_format), [value or 0, build_url(qdict)]

    @property
    def verbose_abscissa(self):
        cfield = self._cfield
        return cfield.name if cfield else '??'


@RGRAPH_HANDS_MAP(AbscissaGroup.CUSTOM_DAY)
class RGHCustomDay(_RGHCustomField):
    verbose_name = _('By days')

    def _fetch(self, *, entities, order, user, extra_q):
        value_rname = self._cfield.value_class._meta.get_field('entity').remote_field.name

        return self._get_custom_dates_values(
            entities=entities,
            kind='day',
            qdict_builder=lambda date: {
                f'{value_rname}__value__year': date.year,
                f'{value_rname}__value__month': date.month,
                f'{value_rname}__value__day': date.day,
            },
            date_format=_generate_date_format(year=True, month=True, day=True),
            order=order,
            extra_q=extra_q,
        )


@RGRAPH_HANDS_MAP(AbscissaGroup.CUSTOM_MONTH)
class RGHCustomMonth(_RGHCustomField):
    verbose_name = _('By months')

    def _fetch(self, *, entities, order, user, extra_q):
        # TODO: factorise with _get_custom_dates_values()?
        value_rname = self._cfield.value_class._meta.get_field('entity').remote_field.name

        return self._get_custom_dates_values(
            entities=entities,
            kind='month',
            qdict_builder=lambda date: {
                f'{value_rname}__value__year':  date.year,
                f'{value_rname}__value__month': date.month,
            },
            date_format=_generate_date_format(year=True, month=True),
            order=order,
            extra_q=extra_q,
        )


@RGRAPH_HANDS_MAP(AbscissaGroup.CUSTOM_YEAR)
class RGHCustomYear(_RGHCustomField):
    verbose_name = _('By years')

    def _fetch(self, *, entities, order, user, extra_q):
        value_rname = self._cfield.value_class._meta.get_field('entity').remote_field.name

        return self._get_custom_dates_values(
            entities=entities,
            kind='year',
            qdict_builder=lambda date: {
                f'{value_rname}__value__year': date.year,
            },
            date_format=_generate_date_format(year=True),
            order=order,
            extra_q=extra_q
        )


@RGRAPH_HANDS_MAP(AbscissaGroup.CUSTOM_RANGE)
class RGHCustomRange(_DateRangeMixin, _RGHCustomField):
    verbose_name = _('By X days')

    def __init__(self, graph):
        super().__init__(graph)

        self._fetch_method = self._fetch_with_group_by
        vendor = connection.vendor
        if vendor not in {'sqlite', 'mysql', 'postgresql'}:
            logger.warning(
                'Report graph data optimizations not available with DB vendor "%s",'
                ' reverting to slower fallback method.',
                vendor,
            )
            self._fetch_method = self._fetch_fallback

        self._days = self.get_days(graph)

    def _fetch(self, *, entities, order, user, extra_q):
        return self._fetch_method(entities, order, extra_q)

    # TODO: This is almost identical to RGHRange and most of it could be factorised together
    def _fetch_with_group_by(self, entities, order, extra_q):
        cfield = self._cfield
        value_meta = cfield.value_class._meta
        value_rname = value_meta.get_field('entity').remote_field.name
        entities = entities.filter(**{f'{value_rname}__custom_field': cfield})

        date_aggregates = entities.aggregate(
            min_date=Min(f'{value_rname}__value'),
            max_date=Max(f'{value_rname}__value'),
        )
        min_date = date_aggregates['min_date']
        max_date = date_aggregates['max_date']

        if min_date is not None and max_date is not None:
            build_url = self._listview_url_builder(extra_q=extra_q)
            days = self._days

            field_name = _physical_field_name(value_meta.db_table, 'value')

            x_value_format = _db_grouping_format()
            x_value_key = (
                x_value_format % (field_name, min_date.strftime("'%Y-%m-%d'"), days)
                if order == 'ASC' else
                x_value_format % (max_date.strftime("'%Y-%m-%d'"), field_name, days)
            )

            intervals = DateInterval.generate(days - 1, min_date, max_date, order)
            aggregates = self._aggregate_by_key(entities, x_value_key, 'ASC')

            label_fmt = _generate_date_format(year=True, month=True, day=True)
            label_sep = '-' if '-' not in label_fmt else '/'

            for interval, value in sparsezip(intervals, aggregates, 0):
                range_label = '{}{}{}'.format(
                    interval.begin.strftime(label_fmt),
                    label_sep,
                    interval.end.strftime(label_fmt),
                )
                url = build_url({
                    f'{value_rname}__custom_field': cfield.id,
                    f'{value_rname}__value__range': [interval.before, interval.after],
                })

                yield range_label, [value, url]

    def _fetch_fallback(self, entities, order, extra_q):
        cfield = self._cfield
        value_rname = cfield.value_class._meta.get_field('entity').remote_field.name
        entities_filter = entities.filter
        date_aggregates = entities_filter(
            **{f'{value_rname}__custom_field': cfield}
        ).aggregate(
            min_date=Min(f'{value_rname}__value'),
            max_date=Max(f'{value_rname}__value'),
        )
        min_date = date_aggregates['min_date']
        max_date = date_aggregates['max_date']

        label_fmt = _generate_date_format(year=True, month=True, day=True)
        label_sep = '-' if '-' not in label_fmt else '/'

        if min_date is not None and max_date is not None:
            y_value_func = self._y_calculator.aggregate
            build_url = self._listview_url_builder(extra_q=extra_q)

            for interval in DateInterval.generate(
                (self._graph.days or 1) - 1, min_date, max_date, order,
            ):
                before = interval.before
                after  = interval.after
                sub_entities = entities_filter(**{
                    f'{value_rname}__custom_field': cfield,
                    f'{value_rname}__value__range': (before, after),
                })

                yield (
                    '{}{}{}'.format(
                        interval.begin.strftime(label_fmt),
                        label_sep,
                        interval.end.strftime(label_fmt),
                    ),
                    [
                        y_value_func(sub_entities),
                        build_url({
                            f'{value_rname}__custom_field': cfield.id,
                            f'{value_rname}__value__range': [
                                interval.before,
                                interval.after,
                            ],
                        }),
                    ]
                )


@RGRAPH_HANDS_MAP(AbscissaGroup.CUSTOM_FK)
class RGHCustomFK(_RGHCustomField):
    verbose_name = _('By values (of custom choices)')

    def _fetch(self, *, entities, order, user, extra_q):
        y_calculator = self._y_calculator
        y_value_func = y_calculator.aggregate
        entities_filter = entities.filter(y_calculator.annotate_extra_q).filter
        build_url = self._listview_url_builder(extra_q=extra_q)
        related_instances = [
            *CustomFieldEnumValue.objects.filter(custom_field=self._cfield),
        ]

        if order == 'DESC':
            related_instances.reverse()

        for instance in related_instances:
            kwargs = {'customfieldenum__value': instance.id}

            yield (
                str(instance),
                [y_value_func(entities_filter(**kwargs)), build_url(kwargs)],
            )
