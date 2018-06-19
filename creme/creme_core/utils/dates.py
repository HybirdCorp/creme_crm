# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from datetime import datetime, date, timedelta
from time import strptime as time_strptime
# import warnings

from django.utils import formats
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, make_naive, is_naive, is_aware, utc  # get_current_timezone


DATE_ISO8601_FMT     = '%Y-%m-%d'
DATETIME_ISO8601_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'


def date_2_dict(d):
    return {'year': d.year, 'month': d.month, 'day': d.day}


# # XXX: it is not true ISO 8601 !!!!
# # XXX: only used by 'activesync'
# def get_dt_to_iso8601_str(dt):
#     """Converts the datetime into a string in iso8601 format without any separator.
#     >>> get_dt_to_iso8601_str(datetime.datetime(2011, 4, 27, 10, 9, 54))
#     '20110427T100954Z'
#     """
#     warnings.warn("get_dt_to_iso8601_str() method is deprecated.", DeprecationWarning)
#
#     return dt.strftime("%Y%m%dT%H%M%SZ")


# # XXX: rename, it is not true ISO 8601 !!!!
# # XXX: only used by 'activesync'
# def get_dt_from_iso8601_str(dt_str):
#     """Builds a datetime instance from a iso8601 (without any separators) formatted string.
#     @throws ValueError
#     >>> get_dt_from_iso8601_str("20110427T100954Z")
#     datetime.datetime(2011, 4, 27, 10, 9, 54)
#     """
#     warnings.warn("get_dt_from_iso8601_str() method is deprecated.", DeprecationWarning)
#
#     return datetime.strptime(dt_str, "%Y%m%dT%H%M%SZ")


# def get_dt_from_json_str(dt_str):
#     warnings.warn("get_dt_from_json_str() method is deprecated; use dt_from_ISO8601() instead.",
#                   DeprecationWarning
#                  )
#     return dt_from_ISO8601(dt_str)


def dt_from_ISO8601(dt_str):
    """Returns a TZ aware datetime parsed from the ISO 8601 format.
    ie: YYYY-MM-DDTHH:mm:ss.sssZ.
    NB: this format is used by Date.toJSON() method in JavaScript):
    @param dt_str: String representing a datetime
    @return A datetime instance.
    @throws ValueError
    """
    return make_aware(datetime.strptime(dt_str, DATETIME_ISO8601_FMT), utc)


# def dt_to_json_str(dt):
#     warnings.warn("dt_to_json_str() method is deprecated; use dt_to_ISO8601() instead.",
#                   DeprecationWarning
#                  )
#
#     return dt.strftime(DATETIME_ISO8601_FMT)


def dt_to_ISO8601(dt):
    """Converts a datetime instance to a string, using the ISO 8601 format."""
    if is_aware(dt):
        dt = to_utc(dt)

    return dt.strftime(DATETIME_ISO8601_FMT)


def date_from_ISO8601(d_str):
    """Returns a date instance parsed from the ISO 8601 format
    (the date part of the format).
    @param d_str: A string representing a date.
    @return A datetime.date instance
    """
    return date(*time_strptime(d_str, DATE_ISO8601_FMT)[:3])


def date_to_ISO8601(d):
    """Converts a datetime.date instance to a string, using the ISO 8601 format
    (only the date part of the format).
    """
    return d.strftime(DATE_ISO8601_FMT)


# def get_dt_from_str(dt_str):
#     warnings.warn("get_dt_from_str() method is deprecated; use dt_from_str() instead.",
#                   DeprecationWarning
#                  )
#     return dt_from_str(dt_str)


def dt_from_str(dt_str):
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


# def get_date_from_str(d_str):
#     warnings.warn("get_date_from_str() method is deprecated; use date_from_str() instead.",
#                   DeprecationWarning
#                  )
#
#     return date_from_str(d_str)


def date_from_str(d_str):
    "Returns a datetime.date from filled formats in settings, or None."
    for fmt in formats.get_format('DATE_INPUT_FORMATS'):
        try:
            return date(*time_strptime(d_str, fmt)[:3])
        except ValueError:
            continue
        except TypeError:
            break


def make_aware_dt(dt, is_dst=False):
    """Returns an aware datetime in the current time-zone.
    @param dt: A (naive) datetime instance.
    @param is_dst: If there is an ambiguity on DST transition
                    False => force the post-DST side of the DST transition [default].
                    True => force the pre-DST side.
                    None => raise an exception.
    @return A (aware) datetime.
    """
    # # return make_aware(dt, get_current_timezone())
    # return get_current_timezone().localize(dt, is_dst=is_dst)
    return make_aware(dt, is_dst=is_dst)


def to_utc(dt):
    "Returns a naive datetime from an aware one (converted in UTC)."
    return make_naive(dt, timezone=utc)


def round_hour(dt):
    "Returns a datetime truncated to the passed hour (ie: minutes, seconds, ... are set to 0)."
    return dt - timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
