# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

import time
from datetime import datetime, date

from django.utils import formats
from django.utils.dateparse import parse_datetime
from django.utils.timezone import get_current_timezone, make_aware, is_naive, utc


def date_2_dict(d):
    return {'year': d.year, 'month': d.month, 'day': d.day}

def get_dt_to_iso8601_str(dt):
    """Converts the datetime into a string in iso8601 format without any separators.
    >>> get_dt_to_iso8601_str(datetime.datetime(2011, 4, 27, 10, 9, 54))
    '20110427T100954Z'
    """
    return dt.strftime("%Y%m%dT%H%M%SZ")

def get_dt_from_iso8601_str(dt_str):
    """Builds a datetime instance from a iso8601 (without any separators) formatted string.
    @throws ValueError
    >>>get_dt_from_iso8601_str("20110427T100954Z")
    datetime.datetime(2011, 4, 27, 10, 9, 54)
    """
    return datetime.strptime(dt_str, "%Y%m%dT%H%M%SZ")

def get_dt_from_json_str(dt_str):
    """Return a TZ aware datetime parsed from the JSON format date (Date.toJSON()
    method in JavaScript): YYYY-MM-DDTHH:mm:ss.sssZ
    @throws ValueError
    """
    return make_aware(datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ"), utc)

def get_dt_from_str(dt_str):
    """Returns a datetime from filled formats in settings, or None.
    Doesn't handle microseconds.
    """
    dt = parse_datetime(dt_str)

    if dt:
        return make_aware_dt(dt) if is_naive(dt) else dt

    for fmt in formats.get_format('DATETIME_INPUT_FORMATS'):
        try:
            return make_aware_dt(datetime(*time.strptime(dt_str, fmt)[:6]))
        except ValueError:
            continue
        except TypeError:
            break

def get_date_from_str(date_str):
    "Returns a date from filled formats in settings, or None."
    for fmt in formats.get_format('DATE_INPUT_FORMATS'):
        try:
            return date(*time.strptime(date_str, fmt)[:3])
        except ValueError:
            continue
        except TypeError:
            break

def make_aware_dt(dt):
    return make_aware(dt, get_current_timezone())
