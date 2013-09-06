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

from __future__ import division

from datetime import datetime, timedelta
from calendar import monthrange
import logging

from django.utils.translation import ugettext_lazy as _

from .dates import make_aware_dt


logger = logging.getLogger(__name__)

_DAY_START = {'hour': 0,  'minute': 0,  'second': 0}
_DAY_END   = {'hour': 23, 'minute': 59, 'second': 59}


def get_month_last_day(year, month):
    return monthrange(year, month)[1]

def get_quarter(month):
    return ((month - 1) // 3) + 1

def get_quarter_dates(year, quarter):
    """@param quarter 1 <= integer <= 4"""
    month = quarter * 3

    return (make_aware_dt(datetime(year=year, month=month - 2, day=1,                               **_DAY_START)),
            make_aware_dt(datetime(year=year, month=month,     day=get_month_last_day(year, month), **_DAY_END))
           )


class DateRange(object):
    name = 'base_date_range' #overload
    verbose_name = u'Date range' #overload

    def __unicode__(self):
        return unicode(self.verbose_name)

    def get_dates(self, now):
        raise NotImplementedError

    def get_q_dict(self, field, now):
        start, end = self.get_dates(now)

        if start:
            if end:
                return {'%s__range' % field: (start, end)}

            return {'%s__gte' % field: start}

        return {'%s__lte' % field: end}


class CustomRange(DateRange):
    def __init__(self, start=None, end=None):
        if start and not isinstance(start, datetime):
            start = make_aware_dt(datetime(year=start.year, month=start.month, day=start.day, **_DAY_START))

        if end and not isinstance(end, datetime):
            end = make_aware_dt(datetime(year=end.year, month=end.month, day=end.day, **_DAY_END))

        self._start = start
        self._end   = end

    def get_dates(self, now):
        return (self._start, self._end)


class PreviousYearRange(DateRange):
    name = 'previous_year'
    verbose_name = _(u'Previous year')

    @staticmethod
    def get_dates(now):
        year = now.year - 1
        return (make_aware_dt(datetime(year=year, month=1,  day=1,  **_DAY_START)),
                make_aware_dt(datetime(year=year, month=12, day=31, **_DAY_END))
               )


class CurrentYearRange(DateRange):
    name = 'current_year'
    verbose_name = _(u'Current year')

    @staticmethod
    def get_dates(now):
        year = now.year
        return (make_aware_dt(datetime(year=year, month=1,  day=1,  **_DAY_START)),
                make_aware_dt(datetime(year=year, month=12, day=31, **_DAY_END))
               )


class NextYearRange(DateRange):
    name = 'next_year'
    verbose_name = _(u'Next year')

    @staticmethod
    def get_dates(now):
        year = now.year + 1
        return (make_aware_dt(datetime(year=year, month=1,  day=1,  **_DAY_START)),
                make_aware_dt(datetime(year=year, month=12, day=31, **_DAY_END))
               )


class PreviousMonthRange(DateRange):
    name = 'previous_month'
    verbose_name = _(u'Previous month')

    @staticmethod
    def get_dates(now):
        if now.month == 1:
            year  = now.year - 1
            start = now.replace(year=year, month=12, day=1,  **_DAY_START)
            end   = now.replace(year=year, month=12, day=31, **_DAY_END)
        else:
            month = now.month - 1
            start = now.replace(month=month, day=1,                                   **_DAY_START)
            end   = now.replace(month=month, day=get_month_last_day(now.year, month), **_DAY_END)

        return (start, end)


class CurrentMonthRange(DateRange):
    name = 'current_month'
    verbose_name = _(u'Current month')

    @staticmethod
    def get_dates(now):
        return (now.replace(day=1,                                       **_DAY_START),
                now.replace(day=get_month_last_day(now.year, now.month), **_DAY_END)
               )


class NextMonthRange(DateRange):
    name = 'next_month'
    verbose_name = _(u'Next month')

    @staticmethod
    def get_dates(now):
        if now.month == 12:
            year  = now.year + 1
            start = now.replace(year=year, month=1, day=1,  **_DAY_START)
            end   = now.replace(year=year, month=1, day=31, **_DAY_END)
        else:
            month = now.month + 1
            start = now.replace(month=month, day=1,                                   **_DAY_START)
            end   = now.replace(month=month, day=get_month_last_day(now.year, month), **_DAY_END)

        return (start, end)


class PreviousQuarterRange(DateRange):
    name = 'previous_quarter'
    verbose_name = _(u'Previous quarter')

    @staticmethod
    def get_dates(now):
        current_quarter = get_quarter(now.month)

        if current_quarter > 1:
            previous_quarter = current_quarter - 1
            year = now.year
        else:
            previous_quarter =  4
            year = now.year - 1

        return get_quarter_dates(year, previous_quarter)


class CurrentQuarterRange(DateRange):
    name = 'current_quarter'
    verbose_name = _(u'Current quarter')

    @staticmethod
    def get_dates(now):
        return get_quarter_dates(now.year, get_quarter(now.month))


class NextQuarterRange(DateRange):
    name = 'next_quarter'
    verbose_name = _(u'Next quarter')

    @staticmethod
    def get_dates(now):
        current_quarter = get_quarter(now.month)

        if current_quarter < 4:
            next_quarter = current_quarter + 1
            year = now.year
        else:
            next_quarter =  1
            year = now.year + 1

        return get_quarter_dates(year, next_quarter)


class FutureRange(DateRange):
    name = 'in_future'
    verbose_name = _(u'In the future')

    @staticmethod
    def get_dates(now):
        return (now, None)


class PastRange(DateRange):
    name = 'in_past'
    verbose_name = _(u'In the past')

    @staticmethod
    def get_dates(now):
        return (None, now)


class YesterdayRange(DateRange):
    name = 'yesterday'
    verbose_name = _(u'Yesterday')

    @staticmethod
    def get_dates(now):
        yesterday = now - timedelta(days=1)
        return (yesterday.replace(**_DAY_START),
                yesterday.replace(**_DAY_END)
               )


class TodayRange(DateRange):
    name = 'today'
    verbose_name = _(u'Today')

    @staticmethod
    def get_dates(now):
        return (now.replace(**_DAY_START),
                now.replace(**_DAY_END)
               )


class TomorrowRange(DateRange):
    name = 'tomorrow'
    verbose_name = _(u'Tomorrow')

    @staticmethod
    def get_dates(now):
        tomorrow = now + timedelta(days=1)
        return (tomorrow.replace(**_DAY_START),
                tomorrow.replace(**_DAY_END)
               )


class DateRangeRegistry(object):
    def __init__(self, *dranges):
        self._ranges = {}
        self.register(*dranges)

    def choices(self):
        return self._ranges.iteritems()

    def register(self, *dranges):
        ranges_map = self._ranges

        for drange in dranges:
            name = drange.name

            if ranges_map.has_key(name):
                logger.warning("Duplicate date range's id or date range registered twice : %s", name) #exception instead ???

            ranges_map[name] = drange

    def get_range(self, name=None, start=None,end=None):
        """
        @param start datetime.date or datetime.date
        @param end datetime.date or datetime.date
        """
        drange = self._ranges.get(name)

        if drange:
            return drange

        if not start and not end:
            return None

        return CustomRange(start, end)


date_range_registry = DateRangeRegistry(PreviousYearRange(), CurrentYearRange(), NextYearRange(),
                                        PreviousMonthRange(), CurrentMonthRange(), NextMonthRange(),
                                        PreviousQuarterRange(), CurrentQuarterRange(), NextQuarterRange(),
                                        FutureRange(), PastRange(),
                                        YesterdayRange(), TodayRange(), TomorrowRange(),
                                       )
