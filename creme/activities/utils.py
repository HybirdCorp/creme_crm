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

def get_last_day_of_a_month(date):
    rdate = date.replace(day=1)
    try:
        rdate = rdate + timedelta(days=31)
    except:
        try:
            rdate = rdate + timedelta(days=30)
        except :
            try :
                rdate = rdate + timedelta(days=29)
            except:
                rdate = rdate + timedelta(days=28)
    return rdate

def get_ical_date(dateTime):
    return "%(year)s%(month)02d%(day)02dT%(hour)02d%(minute)02d%(second)02dZ" % {
        'year' : dateTime.year,
        'month': dateTime.month,
        'day'  : dateTime.day,
        'hour'  : dateTime.hour,
        'minute'  : dateTime.minute,
        'second'  : dateTime.second
    }

def get_ical(events):
    """Return a normalized iCalendar string
    /!\ Each parameter has to be separated by \n ONLY no spaces allowed!
    Example : BEGIN:VCALENDAR\nVERSION:2.0"""
    return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CremeCRM//CremeCRM//EN
%(events)s
END:VCALENDAR"""  % {'events' : "".join([ev.as_ical_event() for ev in events])}
