# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import warning
from datetime import date
from calendar import monthrange

from django.utils.translation import ugettext_lazy as _


def get_month_last_day(year, month):
    return monthrange(year, month)[1]

def get_quarter(month):
    return ((month - 1) // 3) + 1

def get_quarter_dates(year, quarter):
    """@param quarter 1 <= integer <= 4"""
    month = quarter * 3

    return (date(year=year, month=month - 2, day=1),
            date(year=year, month=month,     day=get_month_last_day(year, month))
           )


class DateRange(object):
    name = 'base_date_range' #overload
    verbose_name = u'Date range' #overload

    def __unicode__(self):
        return unicode(self.verbose_name)

    def get_dates(self, today):
        raise NotImplementedError

    def get_q_dict(self, field, today):
        start, end = self.get_dates(today)

        if start:
            if end:
                return {'%s__range' % field: (start, end)}

            return {'%s__gte' % field: start}

        return {'%s__lte' % field: end}


class CustomRange(DateRange):
    def __init__(self, start=None, end=None):
        self._start = start
        self._end   = end

    def get_dates(self, today):
        return (self._start, self._end)


class PreviousYearRange(DateRange):
    name = 'previous_year'
    verbose_name = _(u'Previous year')

    @staticmethod
    def get_dates(today):
        year = today.year - 1
        return (date(year=year, month=1,  day=1),
                date(year=year, month=12, day=31)
               )


class CurrentYearRange(DateRange):
    name = 'current_year'
    verbose_name = _(u'Current year')

    @staticmethod
    def get_dates(today):
        year = today.year
        return (date(year=year, month=1,  day=1),
                date(year=year, month=12, day=31)
               )


class NextYearRange(DateRange):
    name = 'next_year'
    verbose_name = _(u'Next year')

    @staticmethod
    def get_dates(today):
        year = today.year + 1
        return (date(year=year, month=1,  day=1),
                date(year=year, month=12, day=31)
               )

class PreviousMonthRange(DateRange):
    name = 'previous_month'
    verbose_name = _(u'Previous month')

    @staticmethod
    def get_dates(today):
        if today.month == 1:
            year  = today.year - 1
            start = today.replace(year=year, month=12, day=1)
            end   = today.replace(year=year, month=12, day=31)
        else:
            month = today.month - 1
            start = today.replace(month=month, day=1)
            end   = today.replace(month=month, day=get_month_last_day(today.year, month))

        return (start, end)


class CurrentMonthRange(DateRange):
    name = 'current_month'
    verbose_name = _(u'Current month')

    @staticmethod
    def get_dates(today):
        return (today.replace(day=1),
                today.replace(day=get_month_last_day(today.year, today.month))
               )


class NextMonthRange(DateRange):
    name = 'next_month'
    verbose_name = _(u'Next month')

    @staticmethod
    def get_dates(today):
        if today.month == 12:
            year  = today.year + 1
            start = today.replace(year=year, month=1, day=1)
            end   = today.replace(year=year, month=1, day=31)
        else:
            month = today.month + 1
            start = today.replace(month=month, day=1)
            end   = today.replace(month=month, day=get_month_last_day(today.year, month))

        return (start, end)


class PreviousQuarterRange(DateRange):
    name = 'previous_quarter'
    verbose_name = _(u'Previous quarter')

    @staticmethod
    def get_dates(today):
        current_quarter = get_quarter(today.month)

        if current_quarter > 1:
            previous_quarter = current_quarter - 1
            year = today.year
        else:
            previous_quarter =  4
            year = today.year - 1

        return get_quarter_dates(year, previous_quarter)


class CurrentQuarterRange(DateRange):
    name = 'current_quarter'
    verbose_name = _(u'Current quarter')

    @staticmethod
    def get_dates(today):
        return get_quarter_dates(today.year, get_quarter(today.month))


class NextQuarterRange(DateRange):
    name = 'next_quarter'
    verbose_name = _(u'Next quarter')

    @staticmethod
    def get_dates(today):
        current_quarter = get_quarter(today.month)

        if current_quarter < 4:
            next_quarter = current_quarter + 1
            year = today.year
        else:
            next_quarter =  1
            year = today.year + 1

        return get_quarter_dates(year, next_quarter)


class FutureRange(DateRange):
    name = 'in_future'
    verbose_name = _(u'In the future')

    @staticmethod
    def get_dates(today):
        return (today, None)


class PastRange(DateRange):
    name = 'in_past'
    verbose_name = _(u'In the past')

    @staticmethod
    def get_dates(today):
        return (None, today)


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
                warning("Duplicate date range's id or date range registered twice : %s", name) #exception instead ???

            ranges_map[name] = drange

    def get_range(self, name=None, start=None,end=None):
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
                                       )
