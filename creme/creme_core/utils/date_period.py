# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

from __future__ import absolute_import #for collections...

import logging
from collections import OrderedDict

from dateutil.relativedelta import relativedelta

from django.utils.translation import ugettext_lazy as _, ungettext


logger = logging.getLogger(__name__)


class DatePeriod(object):
    name = 'base_date_period' #overload
    verbose_name = u'Date period' #overload

    def __unicode__(self):
        return unicode(self.verbose_name)

    def as_timedelta(self):
        raise NotImplementedError

    def _value_as_dict(self):
        "Period as a jsonifiable dictionary"
        raise NotImplementedError

    def as_dict(self):
        "Period as a jsonifiable dictionary"
        d = {'type': self.name}
        d.update(self._value_as_dict())

        return d


class SimpleValueDatePeriod(DatePeriod):
    def __init__(self, value):
        self._value = value

    def __unicode__(self):
        value = self._value
        return self._ungettext(self._value) % value

    def _ungettext(self, value):
        raise NotImplementedError

    def as_timedelta(self):
        return relativedelta(**{self.name: self._value})

    def _value_as_dict(self):
        return {'value': self._value}


class MinutesPeriod(SimpleValueDatePeriod):
    name = 'minutes'
    verbose_name = _('Minute(s)')

    def _ungettext(self, value):
        return ungettext('%s minute', '%s minutes', value)


class HoursPeriod(SimpleValueDatePeriod):
    name         = 'hours'
    verbose_name = _('Hour(s)')

    def _ungettext(self, value):
        return ungettext('%s hour', '%s hours', value)


class DaysPeriod(SimpleValueDatePeriod):
    name = 'days'
    verbose_name = _('Day(s)')

    def _ungettext(self, value):
        return ungettext('%s day', '%s days', value)


class WeeksPeriod(SimpleValueDatePeriod):
    name = 'weeks'
    verbose_name = _('Week(s)')

    def _ungettext(self, value):
        return ungettext('%s week', '%s weeks', value)


class MonthsPeriod(SimpleValueDatePeriod):
    name = 'months'
    verbose_name = _('Month(s)')

    def _ungettext(self, value):
        return ungettext('%s month', '%s months', value)


class YearsPeriod(SimpleValueDatePeriod):
    name = 'years'
    verbose_name = _('Year(s)')

    def _ungettext(self, value):
        return ungettext('%s year', '%s years', value)


class DatePeriodRegistry(object):
    def __init__(self, *periods):
        self._periods = OrderedDict()
        self.register(*periods)

    def choices(self):
        for name, period_klass in self._periods.iteritems():
            yield name, period_klass.verbose_name

    def get_period(self, name, *args):
        klass = self._periods.get(name)

        if not klass:
            return None

        return klass(*args)

    def deserialize(self, dict_value):
        return self.get_period(dict_value['type'], dict_value['value'])

    def register(self, *periods):
        periods_map = self._periods

        for period in periods:
            name = period.name

            if periods_map.has_key(name):
                logger.warning("Duplicate date period's id or period registered twice : %s", name) #exception instead ???

            periods_map[name] = period


date_period_registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod, DaysPeriod,
                                          WeeksPeriod, MonthsPeriod, YearsPeriod,
                                         )
