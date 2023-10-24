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

import logging
from calendar import monthrange
from collections import OrderedDict
# from datetime import date
from datetime import datetime, timedelta
from typing import Iterator

from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from .date_period import date_period_registry

logger = logging.getLogger(__name__)

_DAY_START = {'hour': 0,  'minute': 0,  'second': 0}
_DAY_END   = {'hour': 23, 'minute': 59, 'second': 59}


def get_month_last_day(year, month):
    return monthrange(year, month)[1]


def get_quarter(month: int) -> int:
    return ((month - 1) // 3) + 1


def get_quarter_dates(year: int, quarter: int):
    """@param quarter: 1 <= integer <= 4"""
    month = quarter * 3

    return (
        make_aware(datetime(
            year=year, month=month - 2, day=1,                               **_DAY_START
        )),
        make_aware(datetime(
            year=year, month=month,     day=get_month_last_day(year, month), **_DAY_END
        ))
    )


class DateRange:
    name: str = 'base_date_range'  # Override in child classes
    verbose_name = 'Date range'  # Override in child classes

    period_registry = date_period_registry

    # TODO: remove? (rework DateFieldHandlerMixin to stop passing start/end when not needed?)
    def __init__(self, **kwargs):
        print(kwargs)  # TODO: remove
        super().__init__()

    def __str__(self):
        return str(self.verbose_name)

    # @staticmethod
    # def get_dates(now):
    #     raise NotImplementedError
    def get_dates(self, now):
        raise NotImplementedError

    def get_q_dict(self, field: str, now, **extra_data) -> dict:
        start, end = self.get_dates(now)

        if start:
            if end:
                return {f'{field}__range': (start, end)}

            return {f'{field}__gte': start}

        return {f'{field}__lte': end}


class CustomRange(DateRange):
    # name = ''
    name = 'custom_range'
    verbose_name = pgettext_lazy('creme_core-date_range', 'Customized')

    def __init__(self, start=None, end=None):
        if start and not isinstance(start, datetime):
            start = make_aware(datetime(
                year=start.year, month=start.month, day=start.day, **_DAY_START
            ))

        if end and not isinstance(end, datetime):
            end = make_aware(datetime(
                year=end.year, month=end.month, day=end.day, **_DAY_END
            ))

        self._start = start
        self._end   = end

    def get_dates(self, now):
        return self._start, self._end


class PreviousYearRange(DateRange):
    name = 'previous_year'
    verbose_name = _('Previous year')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        year = now.year - 1
        return (
            make_aware(datetime(year=year, month=1,  day=1,  **_DAY_START)),
            make_aware(datetime(year=year, month=12, day=31, **_DAY_END))
        )


class CurrentYearRange(DateRange):
    name = 'current_year'
    verbose_name = _('Current year')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        year = now.year
        return (
            make_aware(datetime(year=year, month=1,  day=1,  **_DAY_START)),
            make_aware(datetime(year=year, month=12, day=31, **_DAY_END))
        )


class NextYearRange(DateRange):
    name = 'next_year'
    verbose_name = _('Next year')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        year = now.year + 1
        return (
            make_aware(datetime(year=year, month=1,  day=1,  **_DAY_START)),
            make_aware(datetime(year=year, month=12, day=31, **_DAY_END))
        )


class PreviousMonthRange(DateRange):
    name = 'previous_month'
    verbose_name = _('Previous month')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        if now.month == 1:
            year  = now.year - 1
            start = now.replace(year=year, month=12, day=1,  **_DAY_START)
            end   = now.replace(year=year, month=12, day=31, **_DAY_END)
        else:
            month = now.month - 1
            start = now.replace(month=month, day=1,                                   **_DAY_START)
            end   = now.replace(month=month, day=get_month_last_day(now.year, month), **_DAY_END)

        return start, end


class CurrentMonthRange(DateRange):
    name = 'current_month'
    verbose_name = _('Current month')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        return (
            now.replace(day=1,                                       **_DAY_START),
            now.replace(day=get_month_last_day(now.year, now.month), **_DAY_END)
        )


class NextMonthRange(DateRange):
    name = 'next_month'
    verbose_name = _('Next month')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        if now.month == 12:
            year  = now.year + 1
            start = now.replace(year=year, month=1, day=1,  **_DAY_START)
            end   = now.replace(year=year, month=1, day=31, **_DAY_END)
        else:
            month = now.month + 1
            start = now.replace(month=month, day=1,                                   **_DAY_START)
            end   = now.replace(month=month, day=get_month_last_day(now.year, month), **_DAY_END)

        return start, end


class PreviousQuarterRange(DateRange):
    name = 'previous_quarter'
    verbose_name = _('Previous quarter')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        current_quarter = get_quarter(now.month)

        if current_quarter > 1:
            previous_quarter = current_quarter - 1
            year = now.year
        else:
            previous_quarter = 4
            year = now.year - 1

        return get_quarter_dates(year, previous_quarter)


class CurrentQuarterRange(DateRange):
    name = 'current_quarter'
    verbose_name = _('Current quarter')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        return get_quarter_dates(now.year, get_quarter(now.month))


class NextQuarterRange(DateRange):
    name = 'next_quarter'
    verbose_name = _('Next quarter')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        current_quarter = get_quarter(now.month)

        if current_quarter < 4:
            next_quarter = current_quarter + 1
            year = now.year
        else:
            next_quarter = 1
            year = now.year + 1

        return get_quarter_dates(year, next_quarter)


class FutureRange(DateRange):
    name = 'in_future'
    verbose_name = _('In the future')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        return now, None


class PastRange(DateRange):
    name = 'in_past'
    verbose_name = _('In the past')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        return None, now


class YesterdayRange(DateRange):
    name = 'yesterday'
    verbose_name = _('Yesterday')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        yesterday = now - timedelta(days=1)
        return (
            yesterday.replace(**_DAY_START),
            yesterday.replace(**_DAY_END),
        )


class TodayRange(DateRange):
    name = 'today'
    verbose_name = _('Today')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        return (
            now.replace(**_DAY_START),
            now.replace(**_DAY_END),
        )


class TomorrowRange(DateRange):
    name = 'tomorrow'
    verbose_name = _('Tomorrow')

    # @staticmethod
    # def get_dates(now):
    def get_dates(self, now):
        tomorrow = now + timedelta(days=1)
        return (
            tomorrow.replace(**_DAY_START),
            tomorrow.replace(**_DAY_END),
        )


class YearEquals(DateRange):
    name = 'year_equals'
    verbose_name = _('Year equals …')

    def get_q_dict(self, field, *args, **extra_data):
        return {f'{field}__year': extra_data['year']}


class InMoreThan(DateRange):
    name = 'in_more_than'
    verbose_name = _('In more than …')

    def get_q_dict(self, field, now, **extra_data):
        return {
            f'{field}__gt': now + self.period_registry.deserialize(extra_data['period'])
                                                      .as_timedelta(),
        }


class InLessThan(DateRange):
    name = 'in_less_than'
    verbose_name = _('In less than …')

    def get_q_dict(self, field, now, **extra_data):
        return {
            f'{field}__range': (
                now,
                now + self.period_registry.deserialize(extra_data['period'])
                                          .as_timedelta(),
            ),
        }


class MoreThanAgo(DateRange):
    name = 'more_than_ago'
    verbose_name = _('More than … ago')

    def get_q_dict(self, field, now, **extra_data):
        return {
            f'{field}__lt': now - self.period_registry.deserialize(extra_data['period'])
                                                      .as_timedelta(),
        }


class LessThanAgo(DateRange):
    name = 'less_than_ago'
    verbose_name = _('Less than … ago')

    def get_q_dict(self, field, now, **extra_data):
        return {
            f'{field}__range': (
                now - self.period_registry.deserialize(extra_data['period'])
                                          .as_timedelta(),
                now,
            ),
        }


class EmptyRange(DateRange):
    name = 'empty'
    verbose_name = _('Is empty')

    # def get_q_dict(self, field, now):
    def get_q_dict(self, field, *args, **kwargs):
        return {f'{field}__isnull': True}


class NotEmptyRange(DateRange):
    name = 'not_empty'
    verbose_name = _('Is not empty')

    # def get_q_dict(self, field, now):
    def get_q_dict(self, field, *args, **kwargs):
        return {f'{field}__isnull': False}


class DateRangeRegistry:
    class RegistrationError(Exception):
        pass

    # def __init__(self, *dranges: DateRange):
    #     self._ranges: dict[str, DateRange] = OrderedDict()
    #     self.register(*dranges)
    def __init__(self, *dranges: type[DateRange]):
        self._ranges: dict[str, type[DateRange]] = OrderedDict()
        self.register(*dranges)

    # def choices(self, exclude_empty=True):
    #     if exclude_empty:
    #         empties = frozenset((EmptyRange.name, NotEmptyRange.name))
    #         return (
    #             (key, d_range)
    #             for key, d_range in self._ranges.items()
    #             if key not in empties
    #         )
    #
    #     return self._ranges.items()
    def choices(self, exclude_empty=True) -> Iterator[tuple[str, str]]:
        # if exclude_empty:
        #     empties = frozenset((EmptyRange.name, NotEmptyRange.name))
        #     return (
        #         (key, d_range)
        #         for key, d_range in self._ranges.items()
        #         if key not in empties
        #     )
        #
        # return self._ranges.items()
        excluded = {EmptyRange.name, NotEmptyRange.name} if exclude_empty else ()
        for range_name, range_cls in self._ranges.items():
            if range_name not in excluded:
                yield range_name, range_cls.verbose_name

    # def register(self, *dranges: DateRange) -> None:
    def register(self, *dranges: type[DateRange]) -> None:
        ranges_map = self._ranges

        for drange in dranges:
            name = drange.name

            if name in ranges_map:
                raise self.RegistrationError(
                    f"Duplicate date range's id or date range registered twice : {name}"
                )

            ranges_map[name] = drange

    # def get_range(self,
    #               name: str | None = None,
    #               start: date | None = None,
    #               end: date | None = None,
    #               ) -> DateRange | None:
    #     """Get a DateRange.
    #     @param name: Name of a registered range (e.g. "next_year"),
    #            or None if you want a custom range.
    #     @param start: Start date of custom range.
    #            Instance of <datetime.date>, or None (named range, only end date).
    #     @param end: End date of custom range.
    #            Instance of <datetime.date>, or None (named range, only start date).
    #     @return: An instance of DateRange, or None.
    #     """
    #     if name:
    #         drange = self._ranges.get(name)
    #
    #         if drange:
    #             return drange
    #         else:
    #             logger.warning(
    #                 '%s.get_range(): no range named "%s".',
    #                 type(self).__name__, name,
    #             )
    #
    #     if not start and not end:
    #         return None
    #
    #     return CustomRange(start, end)
    def get_range(self,
                  name: str,
                  # start: date | None = None,
                  # end: date | None = None,
                  **kwargs,
                  ) -> DateRange | None:
        """Get a DateRange.
        @param name: Name of a registered range (e.g. "next_year"),
               or None if you want a custom range.
        @param start: Start date of custom range.
               Instance of <datetime.date>, or None (named range, only end date).
        @param end: End date of custom range.
               Instance of <datetime.date>, or None (named range, only start date).
        @return: An instance of DateRange, or None.
        """
        drange = self._ranges.get(name)

        if not drange:
            logger.warning(
                '%s.get_range(): no range named "%s".',
                type(self).__name__, name,
            )
            return None  # TODO: exception

        # TODO: try..except.. ?
        return drange(**kwargs)


# date_range_registry = DateRangeRegistry(
#     PreviousYearRange(),    CurrentYearRange(),    NextYearRange(),
#     PreviousQuarterRange(), CurrentQuarterRange(), NextQuarterRange(),
#     PreviousMonthRange(),   CurrentMonthRange(),   NextMonthRange(),
#     YesterdayRange(), TodayRange(), TomorrowRange(),
#     FutureRange(), PastRange(),
#     YearEquals(),
#     InMoreThan(), InLessThan(), MoreThanAgo(), LessThanAgo(),
#     EmptyRange(), NotEmptyRange(),
# )
date_range_registry = DateRangeRegistry(
    CustomRange,
    PreviousYearRange,    CurrentYearRange,    NextYearRange,
    PreviousQuarterRange, CurrentQuarterRange, NextQuarterRange,
    PreviousMonthRange,   CurrentMonthRange,   NextMonthRange,
    YesterdayRange, TodayRange, TomorrowRange,
    FutureRange, PastRange,
    YearEquals,
    InMoreThan, InLessThan, MoreThanAgo, LessThanAgo,
    EmptyRange, NotEmptyRange,
)
