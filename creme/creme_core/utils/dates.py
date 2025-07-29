################################################################################
#
# Copyright (c) 2009-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from datetime import date, datetime, timedelta, timezone
from time import strptime as time_strptime

from django.utils import formats
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, is_naive, make_aware, make_naive

# NB:
#  - years between in [0001, 1582] are not standardized; we chose to pad with 0
#  - when we use '%Y' & a year < 1000, strftime() does not pad with 0,
#    but strptime() only recognized year with 0 padding...
#  - the format '%4Y' is recognized by strftime() but no strptime()...
# TODO: add other constants with '%4Y'? remove constants?
DATE_ISO8601_FMT     = '%Y-%m-%d'
DATETIME_ISO8601_FMT = '%Y-%m-%dT%H:%M:%S.%fZ'


def date_2_dict(d: date) -> dict:
    return {'year': d.year, 'month': d.month, 'day': d.day}


def dt_from_ISO8601(dt_str: str) -> datetime:
    """Returns a TZ aware datetime parsed from the ISO 8601 format.
    ie: YYYY-MM-DDTHH:mm:ss.sssZ.
    NB: this format is used by Date.toJSON() method in JavaScript.
    @param dt_str: String representing a datetime.
    @return A datetime instance.
    @throws ValueError
    """
    return make_aware(datetime.strptime(dt_str, DATETIME_ISO8601_FMT), timezone=timezone.utc)


def dt_to_ISO8601(dt: datetime) -> str:
    """Converts a datetime instance to a string, using the ISO 8601 format."""
    if is_aware(dt):
        dt = to_utc(dt)

    # return dt.strftime(f'%4Y-%m-%dT%H:%M:%S.%fZ')
    # The behaviour of strftime for '%4Y' is not consistent between OS
    # (see https://bugs.python.org/issue13305)
    return dt.strftime(f'{dt.year:04d}-%m-%dT%H:%M:%S.%fZ')


def date_from_ISO8601(d_str: str) -> date:
    """Returns a date instance parsed from the ISO 8601 format
    (the date part of the format).
    @param d_str: A string representing a date.
    @return A datetime.date instance.
    """
    return date(*time_strptime(d_str, DATE_ISO8601_FMT)[:3])


def date_to_ISO8601(d: date) -> str:
    """Converts a <datetime.date> instance to a string, using the ISO 8601 format
    (only the date part of the format).
    """
    # See comment in dt_to_ISO8601()
    # return d.strftime('%4Y-%m-%d')
    return d.strftime(f'{d.year:04d}-%m-%d')


def dt_from_str(dt_str: str) -> datetime | None:
    """Returns a datetime from filled formats in settings, or None.
    Doesn't handle microseconds.
    """
    dt = parse_datetime(dt_str)

    if dt:
        return make_aware(dt) if is_naive(dt) else dt

    for fmt_name in ('DATETIME_INPUT_FORMATS', 'DATE_INPUT_FORMATS'):
        for fmt in formats.get_format(fmt_name):
            try:
                return make_aware(datetime(*time_strptime(dt_str, fmt)[:6]))
            except ValueError:
                continue
            except TypeError:
                break

    return None


def date_from_str(d_str: str) -> date | None:
    "Returns a datetime.date from filled formats in settings, or None."
    for fmt in formats.get_format('DATE_INPUT_FORMATS'):
        try:
            return date(*time_strptime(d_str, fmt)[:3])
        except ValueError:
            continue
        except TypeError:
            break

    return None


def to_utc(dt: datetime) -> datetime:
    "Returns a naive datetime from an aware one (converted in UTC)."
    return make_naive(dt, timezone=timezone.utc)


def round_hour(dt: datetime) -> datetime:
    "Returns a datetime truncated to the passed hour (i.e. minutes, seconds, … are set to 0)."
    return dt - timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
