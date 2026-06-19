################################################################################
#
# Copyright (c) 2009-2026 Hybird
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
#
################################################################################

import logging
import sys
import traceback
import warnings
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.http import Http404
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

# from ..signals import pre_replace_related
logger = logging.getLogger(__name__)


def _get_from_request_or_404(method, method_name, key, cast=None, **kwargs):
    """@param cast: A function that casts the return value, and raise an
              Exception if it is not possible (e.g. int).
    """
    value = method.get(key)

    if value is None:
        if 'default' not in kwargs:
            msg = f'No {method_name} argument with this key: "{key}".'
            logger.warning(msg)

            raise Http404(msg)

        value = kwargs['default']

    if cast:
        try:
            value = cast(value)
        except Exception as e:
            msg = f'Problem with argument "{key}": it can not be coerced ({e})'
            logger.warning(msg)

            raise Http404(msg) from e

    return value


def get_from_GET_or_404(GET, key, cast=None, **kwargs):
    return _get_from_request_or_404(GET, 'GET', key, cast, **kwargs)


def get_from_POST_or_404(POST, key, cast=None, **kwargs):
    return _get_from_request_or_404(POST, 'POST', key, cast, **kwargs)


def entities_to_str(entities: Iterable, user) -> str:
    """Return a string representing an iterable of CremeEntities,
    with care of permissions.
    """
    return ', '.join(entity.allowed_str(user) for entity in entities)


def bool_from_str_extended(value: str) -> bool:
    value = value.lower()
    if value in {'1', 'true'}:
        return True

    if value in {'0', 'false'}:
        return False

    raise ValueError(
        f'Can not be coerced to a boolean value: {value}; must be in 0/1/false/true'
    )


@mark_safe
def bool_as_html(b: bool) -> str:
    if b:
        checked = 'checked '
        label = _('Yes')
    else:
        checked = ''
        label = _('No')

    return f'<input type="checkbox" {checked}disabled/>{label}'


def as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def round_decimal(value: Decimal, mode=ROUND_HALF_UP) -> Decimal:
    """Returns a rounded Decimal instance with 2 decimal places.
    @param mode: Rounding policy of the decimal module like
           decimal.ROUND_UP, decimal.ROUND_DOWN or decimal.ROUND_HALF_EVEN.

    >> round_decimal(decimal.Decimal('12')
    Decimal('12.00')

    >> round_decimal(decimal.Decimal('14.25639')
    Decimal('14.26')
    """
    try:
        return Decimal(value).quantize(Decimal('.01'), rounding=mode)
    except InvalidOperation:
        # TODO: test
        logger.exception('Error when rounding: %s', value)
        return Decimal()


_I2R_NUMERAL_MAP = [
    (1000, 'M'),  (900, 'CM'), (500, 'D'),  (400, 'CD'), (100, 'C'),
    (90,   'XC'), (50,  'L'),  (40,  'XL'), (10,  'X'),  (9,   'IX'),
    (5,    'V'),  (4,   'IV'), (1,   'I'),
]


# Thx to: http://www.daniweb.com/software-development/python/code/216865/roman-numerals-python
def int_2_roman(i: int) -> str:
    "Convert an integer to its roman representation (string)."
    if i >= 4000:
        logger.critical('int_2_roman() should not be used with values >= 4000')
        return '?'

    result = []

    for value, numeral in _I2R_NUMERAL_MAP:
        while i >= value:
            result.append(numeral)
            i -= value

    return ''.join(result)


def truncate_str(str: str, max_length: int, suffix: str = '') -> str:
    """Truncate a suffixed string to a maximum length ; priority is given to keep the whole suffix,
     excepted when this one is too long.

    @param str: The original string (a str instance).
    @param max_length: The maximum length (integer).
    @param suffix: A str instance.
    @return: The truncated string (a str instance).

    >> truncate_str('my_entity_with_a_long_name', 24, suffix='#2')
    'my_entity_with_a_long_#2'
    """
    warnings.warn(
        'truncate_str() is deprecated; '
        'use creme_core.utils.string.suffixed_truncate() instead.',
        DeprecationWarning,
    )

    if max_length <= 0:
        return ''

    len_str = len(str)
    if len_str <= max_length and not suffix:
        return str

    total = max_length - len(suffix)
    if total > 0:
        return str[:total] + suffix
    elif total == 0:
        return suffix
    else:
        return str[:max_length]


def ellipsis(s: str, length: int) -> str:
    "Ensures that a string has a maximum length."
    warnings.warn(
        'ellipsis() is deprecated; '
        'use django.utils.text.Truncator.chars() instead.',
        DeprecationWarning,
    )
    if len(s) > length:
        s = s[:length - 1] + '…'

    return s


def ellipsis_multi(strings: Iterable[str], length: int) -> list[str]:
    """Return (potentially) shorter strings in order to the global length
    does not exceed a given value.
    Strings are shortened in a way which tends to make them of the same length.

    @param strings: Iterable of str instances.
    @param length: Global (maximum) length (i.e. integer).
    @return: A list of str instances.

    >> ellipsis_multi(['123456', '12', '12'], 9)
    ['1234…', '12', '12']
    """
    warnings.warn(
        'ellipsis_multi() is deprecated; '
        'use creme_core.utils.string.multi_truncate() instead.',
        DeprecationWarning,
    )

    class StringToTruncate:
        __slots__ = ('length', 'data')

        def __init__(self, s: str):
            self.length = len(s)
            self.data = s

    str_2_truncate = [StringToTruncate(s) for s in strings]
    total_len = sum(elt.length for elt in str_2_truncate)

    for i in range(max(0, total_len - length)):
        max_idx = -1
        max_value = -1

        for idx, elt in enumerate(str_2_truncate):
            if elt.length > max_value:
                max_value = elt.length
                max_idx = idx

        str_2_truncate[max_idx].length -= 1

    return [ellipsis(elt.data, elt.length) for elt in str_2_truncate]


def log_traceback(logger, limit=10) -> None:  # TODO: use traceback.format_exc() ?
    exc_type, exc_value, exc_traceback = sys.exc_info()

    for line in traceback.format_exception(exc_type, exc_value, exc_traceback, limit=limit):
        for split_line in line.split('\n'):
            logger.error(split_line)


def print_traceback(limit=10) -> None:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=limit)


def __getattr__(name):
    if name == 'update_model_instance':
        from .model import update_model_instance

        warnings.warn(
            'The function "update_model_instance()" has been moved to <creme_core.utils.model>.',
            DeprecationWarning,
        )
        return update_model_instance

    if name == 'replace_related_object':
        from .model import replace_related_object

        warnings.warn(
            'The function "replace_related_object()" has been moved to <creme_core.utils.model>.',
            DeprecationWarning,
        )
        return replace_related_object

    if name == 'prefixed_truncate':
        from .string import prefixed_truncate

        warnings.warn(
            'The function "prefixed_truncate()" has been moved to <creme_core.utils.string>.',
            DeprecationWarning,
        )
        return prefixed_truncate

    if name == 'safe_unicode':
        from .string import safe_unicode

        warnings.warn(
            'The function "safe_unicode()" has been moved to <creme_core.utils.string>.',
            DeprecationWarning,
        )
        return safe_unicode

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
