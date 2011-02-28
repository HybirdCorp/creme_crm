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

from datetime import date, MAXYEAR
from calendar import monthrange

from django.utils.translation import ugettext_lazy as _

from creme_core.date_filters_registry import DatetimeFilter


MONTH_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
quarterMap    = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4, 11: 4, 12: 4}
quarterMonths = {1: [1, 2, 3,], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}

def get_years_month_last_day(years):
    return dict(('%s-%s' % (year, month), monthrange(year,month)[1]) for year in years for month in range(1,13))

def get_months_last_days(y):
    return [monthrange(year,month)[1] for year in [y] for month in range(1,13)]

def get_month_last_day(y, m):
    months = get_months_last_days(y)
    if(m > 0):
        return months[m-1]
    else:
        return months[m]

def last_year_beg(filter, now):
    return date(year=now.year-1, month=1, day=1)

def last_year_end(filter, now):
    return date(year=now.year-1, month=12, day=31)

def current_year_beg(filter, now):
    return now.date().replace(day=1,month=1)

def current_year_end(filter, now):
    return now.date().replace(day=31,month=12)

def next_year_beg(filter, now):
    return now.date().replace(day=1, month=1, year=now.year+1)

def next_year_end(filter, now):
    return now.date().replace(day=31, month=12, year=now.year+1)

def current_month_beg(filter, now):
    return now.date().replace(day=1)

def current_month_end(filter, now):
    return now.date().replace(day=get_month_last_day(now.year, now.month))

def last_month_beg(filter, now):
    if now.month == 1:
        return now.date().replace(day=1, month=12, year=now.year-1)
    return now.date().replace(day=1, month=now.month-1)

def last_month_end(filter, now):
    if now.month == 1:
        return now.date().replace(day=31, month=12, year=now.year-1)
    return now.date().replace(day=get_month_last_day(now.year, now.month-1), month=now.month-1)

def next_month_beg(filter, now):
    if now.month == 12:
        return now.date().replace(day=1, month=1, year=now.year+1)
    return now.date().replace(day=1, month=now.month+1)

def next_month_end(filter, now):
    if now.month == 12:
        return now.date().replace(day=31, month=1, year=now.year+1)
    return now.date().replace(day=get_month_last_day(now.year, now.month+1), month=now.month+1)

def last_quarter_beg(filter, now):
    q1_month = MONTH_NUMBERS[now.month-4]
    q1_year = now.year if q1_month < now.month else now.year-1
    return date(year=q1_year, month=q1_month, day=1)

def last_quarter_end(filter, now):
    q3_month = MONTH_NUMBERS[now.month-2]
    q3_year = now.year if q3_month < now.month else now.year-1
    return date(year=q3_year, month=q3_month, day=get_month_last_day(q3_year, q3_month))

def current_quarter_beg(filter, now):
    months = quarterMonths.get(quarterMap.get(now.month))
    return date(year=now.year, month=months[0], day=1)

def current_quarter_end(filter, now):
    months = quarterMonths.get(quarterMap.get(now.month))
    return date(year=now.year, month=months[-1], day=get_month_last_day(now.year, months[-1]))

def next_quarter_beg(filter, now):
    q1_month = MONTH_NUMBERS[-12+now.month]
    q1_year = now.year if q1_month > now.month else now.year-1
    return date(year=q1_year, month=q1_month, day=1)

def next_quarter_end(filter, now):
    q3_month = MONTH_NUMBERS[-12+now.month+2]
    q3_year = now.year if q3_month > now.month else now.year-1
    return date(year=q3_year, month=q3_month, day=get_month_last_day(q3_year, q3_month))

def in_future_beg(filter, now):
    return now

def in_future_end(filter, now):
    return date(year=MAXYEAR, month=12, day=31)


to_register = (
    ('customized',   DatetimeFilter('customized', _(u"Customized"), lambda x,y: "", lambda x,y: "", is_volatile=False)),

    ('last_year',    DatetimeFilter('last_year',    _(u"Last year"),    last_year_beg,    last_year_end)),
    ('current_year', DatetimeFilter('current_year', _(u"Current year"), current_year_beg, current_year_end)),
    ('next_year',    DatetimeFilter('next_year',    _(u"Next year"),    next_year_beg,    next_year_end)),

    ('last_month',    DatetimeFilter('last_month',    _(u"Last month"),    last_month_beg,    last_month_end)),
    ('current_month', DatetimeFilter('current_month', _(u"Current month"), current_month_beg, current_month_end)),
    ('next_month',    DatetimeFilter('next_month',    _(u"Next month"),    next_month_beg,    next_month_end)),

    ('last_quarter',    DatetimeFilter('last_quarter',    _(u"Last quarter"),    last_quarter_beg,    last_quarter_end)),
    ('current_quarter', DatetimeFilter('current_quarter', _(u"Current quarter"), current_quarter_beg, current_quarter_end)),
    ('next_quarter',    DatetimeFilter('next_quarter',    _(u"Next quarter"),    next_quarter_beg,    next_quarter_end)),
    ('in_future',       DatetimeFilter('in_future',       _(u"In the future"),    in_future_beg,    in_future_end)),

)


