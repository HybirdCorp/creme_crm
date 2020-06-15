# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from datetime import date, datetime, timedelta
from time import strptime as time_strptime
from typing import Optional

from django.utils import formats
from django.utils.dateparse import parse_datetime
from django.utils.timezone import (
    is_aware,
    is_naive,
    make_aware,
    make_naive,
    utc,
)

DATE_ISO8601_FMT     = '%Y-%m-%d'
DATETIME_ISO8601_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'


def date_2_dict(d: date) -> dict:
    return {'year': d.year, 'month': d.month, 'day': d.day}


def dt_from_ISO8601(dt_str: str) -> datetime:
    """Returns a TZ aware datetime parsed from the ISO 8601 format.
    ie: YYYY-MM-DDTHH:mm:ss.sssZ.
    NB: this format is used by Date.toJSON() method in JavaScript):
    @param dt_str: String representing a datetime.
    @return A datetime instance.
    @throws ValueError
    """
    return make_aware(datetime.strptime(dt_str, DATETIME_ISO8601_FMT), utc)


def dt_to_ISO8601(dt: datetime) -> str:
    """Converts a datetime instance to a string, using the ISO 8601 format."""
    if is_aware(dt):
        dt = to_utc(dt)

    return dt.strftime(DATETIME_ISO8601_FMT)


def date_from_ISO8601(d_str: str) -> date:
    """Returns a date instance parsed from the ISO 8601 format
    (the date part of the format).
    @param d_str: A string representing a date.
    @return A datetime.date instance
    """
    return date(*time_strptime(d_str, DATE_ISO8601_FMT)[:3])


def date_to_ISO8601(d: date) -> str:
    """Converts a datetime.date instance to a string, using the ISO 8601 format
    (only the date part of the format).
    """
    return d.strftime(DATE_ISO8601_FMT)


def dt_from_str(dt_str: str) -> Optional[datetime]:
    """Returns a datetime from filled formats in settings, or None.
    Doesn't handle microseconds.
    """
    dt = parse_datetime(dt_str)

    if dt:
        return make_aware_dt(dt) if is_naive(dt) else dt

    for fmt in formats.get_format('DATETIME_INPUT_FORMATS'):
        try:
            return make_aware_dt(datetime(*time_strptime(dt_str, fmt)[:6]))
        except ValueError:
            continue
        except TypeError:
            break

    return None


def date_from_str(d_str: str) -> Optional[date]:
    "Returns a datetime.date from filled formats in settings, or None."
    for fmt in formats.get_format('DATE_INPUT_FORMATS'):
        try:
            return date(*time_strptime(d_str, fmt)[:3])
        except ValueError:
            continue
        except TypeError:
            break

    return None


def make_aware_dt(dt: datetime, is_dst: Optional[bool] = False) -> datetime:
    """Returns an aware datetime in the current time-zone.
    @param dt: A (naive) datetime instance.
    @param is_dst: If there is an ambiguity on DST transition
                    False => force the post-DST side of the DST transition [default].
                    True => force the pre-DST side.
                    None => raise an exception.
    @return A (aware) datetime.
    """
    return make_aware(dt, is_dst=is_dst)


def to_utc(dt: datetime) -> datetime:
    "Returns a naive datetime from an aware one (converted in UTC)."
    return make_naive(dt, timezone=utc)


def round_hour(dt: datetime) -> datetime:
    "Returns a datetime truncated to the passed hour (ie: minutes, seconds, ... are set to 0)."
    return dt - timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
