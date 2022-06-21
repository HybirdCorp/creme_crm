# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2009-2021 Hybird
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
# import warnings
from typing import Callable, Iterable, List, Tuple, TypeVar

from django.http import Http404
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from ..signals import pre_replace_related

logger = logging.getLogger(__name__)
T = TypeVar('T')


# def creme_entity_content_types():
#     warnings.warn(
#         'creme_core.utils.creme_entity_content_types() is deprecated ; '
#         'use creme_core.utils.content_type.entity_ctypes() instead.',
#         DeprecationWarning
#     )
#
#     from . import content_type
#     return content_type.entity_ctypes()


# def get_ct_or_404(ct_id):
#     warnings.warn(
#         'creme_core.utils.get_ct_or_404() is deprecated ; '
#         'use creme_core.utils.content_type.get_ctype_or_404() instead.',
#         DeprecationWarning
#     )
#
#     from . import content_type
#     return content_type.get_ctype_or_404(ct_id)


# def build_ct_choices(ctypes):
#     warnings.warn(
#         'creme_core.utils.build_ct_choices() is deprecated ; '
#         'use creme_core.utils.content_type.ctype_choices() instead.',
#         DeprecationWarning
#     )
#
#     from . import content_type
#     return content_type.ctype_choices(ctypes)


def create_if_needed(model, get_dict, **attrs):
    try:
        instance = model.objects.get(**get_dict)
    except model.DoesNotExist:
        attrs.update(get_dict)
        instance = model.objects.create(**attrs)

    return instance


def update_model_instance(obj, **fields):
    """Update the field values of an instance, and save it only if it has changed."""
    save = False

    for f_name, f_value in fields.items():
        if getattr(obj, f_name) != f_value:
            setattr(obj, f_name, f_value)
            save = True

    # TODO: save only modified fields ?
    if save:
        obj.save()

    return save


def replace_related_object(old_instance, new_instance):
    "Replace the references to an instance by references to another one."
    from ..models import HistoryLine

    pre_replace_related.send(
        sender=old_instance.__class__,
        old_instance=old_instance,
        new_instance=new_instance,
    )  # send_robust() ??

    meta = old_instance._meta
    mark = HistoryLine.mark_as_reassigned

    for rel_objects in (f for f in meta.get_fields() if f.one_to_many):
        field_name = rel_objects.field.name

        for rel_object in getattr(old_instance, rel_objects.get_accessor_name()).all():
            mark(
                rel_object,
                old_reference=old_instance,
                new_reference=new_instance,
                field_name=field_name,
            )
            setattr(rel_object, field_name, new_instance)
            rel_object.save()

    for rel_objects in (
            f
            for f in meta.get_fields(include_hidden=True)
            if f.many_to_many and f.auto_created
    ):
        field_name = rel_objects.field.name

        for rel_object in getattr(old_instance, rel_objects.get_accessor_name()).all():
            m2m_mngr = getattr(rel_object, field_name)
            m2m_mngr.add(new_instance)
            m2m_mngr.remove(old_instance)


def _get_from_request_or_404(method, method_name, key, cast=None, **kwargs):
    """@param cast: A function that cast the return value,
                    and raise an Exception if it is not possible (eg: int).
    """
    value = method.get(key)

    if value is None:
        if 'default' not in kwargs:
            raise Http404(f'No {method_name} argument with this key: "{key}".')

        value = kwargs['default']

    if cast:
        try:
            value = cast(value)
        except Exception as e:
            raise Http404(
                f'Problem with argument "{key}" : it can not be coerced ({e})'
            ) from e

    return value


def get_from_GET_or_404(GET, key, cast=None, **kwargs):
    return _get_from_request_or_404(GET, 'GET', key, cast, **kwargs)


def get_from_POST_or_404(POST, key, cast=None, **kwargs):
    return _get_from_request_or_404(POST, 'POST', key, cast, **kwargs)


def find_first(iterable, function, *default):
    """Returns the first element of an iterable which corresponds to a constraint.
    @param function: Callable which takes one argument (an element form "iterable")
           & returns a value used as a boolean ('True' to accept the element).
    @param default: Optional argument ; if given, it is returned if no element is found.
    @raise IndexError.
    """
    for elt in iterable:
        if function(elt):
            return elt

    if default:
        return default[0]

    raise IndexError


def split_filter(predicate: Callable[[T], bool],
                 iterable: Iterable[T],
                 ) -> Tuple[List[T], List[T]]:
    """Split an iterable into 2 lists : accepted elements & rejected elements
    @param predicate: A callable which takes one argument (an element from "iterable")
           & returns a value used as a boolean ('True' to accept the element).
    @return: 2 lists (accepted then rejected).
    """
    ok = []
    ko = []

    for x in iterable:
        if predicate(x):
            ok.append(x)
        else:
            ko.append(x)

    return ok, ko


# def entities2unicode(entities: Iterable, user) -> str:
#     """Return a string representing an iterable of CremeEntities,
#     with care of permissions.
#     """
#     warnings.warn('entities2unicode() is deprecated ; '
#                   'use entities_to_str() instead.',
#                   DeprecationWarning
#                  )
#     return entities_to_str(entities, user)


def entities_to_str(entities: Iterable, user) -> str:
    """Return a string representing an iterable of CremeEntities,
    with care of permissions.
    """
    return ', '.join(entity.allowed_str(user) for entity in entities)


# def related2unicode(entity, user) -> str:
#     """Return a string representing a related entity with its owner,
#     with care of permissions of this owner.
#     """
#     warnings.warn('related2unicode() is deprecated.',
#                   DeprecationWarning
#                  )
#     return f'{entity.get_related_entity().allowed_str(user)} - {entity}'


__BFS_MAP = {
    'true':  True,
    'false': False,
}


def bool_from_str(string: str) -> bool:
    b = __BFS_MAP.get(string.lower())

    if b is not None:
        return b

    raise ValueError(f'Can not be coerced to a boolean value: {string}')


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


_I2R_NUMERAL_MAP = [
    (1000, 'M'),  (900, 'CM'), (500, 'D'),  (400, 'CD'), (100, 'C'),
    (90,   'XC'), (50,  'L'),  (40,  'XL'), (10,  'X'),  (9,   'IX'),
    (5,    'V'),  (4,   'IV'), (1,   'I'),
]


# Thx to: http://www.daniweb.com/software-development/python/code/216865/roman-numerals-python
def int_2_roman(i: int) -> str:
    "Convert an integer to its roman representation (string)."
    assert i < 4000

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


# TODO: use django.utils.text.Truncator.chars() instead ??
def ellipsis(s: str, length: int) -> str:
    "Ensures that a string has a maximum length."
    if len(s) > length:
        s = s[:length - 1] + '…'

    return s


def ellipsis_multi(strings: Iterable[str], length: int) -> List[str]:
    """Return (potentially) shorter strings in order to the global length
    does not exceed a given value.
    Strings are shortened in a way which tends to make them of the same length.

    @param strings: Iterable of str instances.
    @param length: Global (maximum) length (ie: integer).
    @return: A list of str instances.

    >> ellipsis_multi(['123456', '12', '12'], 9)
    ['1234…', '12', '12']
    """
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


def prefixed_truncate(s: str, prefix, length: int) -> str:
    """Truncates a string if it is too long ; when a truncation is done, the given prefix is added.
    The length of the result is always less than or equal than the given length.

    @param s: A str instance.
    @param prefix: An object which can be "stringified" ; eg: a string, a gettext_lazy instance.
    @param length: An integer.
    @return: A str.
    """
    if len(s) <= length:
        return s

    rem_len = length - len(prefix)
    if rem_len < 0:
        raise ValueError('Prefix is too short for this length')

    return prefix + s[:rem_len]


def safe_unicode(value, encodings=None):
    if isinstance(value, str):
        return value

    if isinstance(value, bytes):
        for encoding in (encodings or ('utf-8', 'cp1252', 'iso-8859-1')):
            try:
                return value.decode(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return value.decode(encoding='utf-8', errors='replace')

    return str(value)


def log_traceback(logger, limit=10) -> None:  # TODO: use traceback.format_exc() ?
    exc_type, exc_value, exc_traceback = sys.exc_info()

    for line in traceback.format_exception(exc_type, exc_value, exc_traceback, limit=limit):
        for split_line in line.split('\n'):
            logger.error(split_line)


def print_traceback(limit=10) -> None:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=limit)
