# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

import re
from html.entities import entitydefs as html_entities
from typing import Callable, Dict, Sequence, Union

import bleach
from django.conf import settings
from django.utils.encoding import force_str  # force_text
from django.utils.html import mark_safe

_AllowedAttributesDict = Dict[str, Union[Sequence[str], Callable[[str, str, str], bool]]]

IMG_SAFE_ATTRIBUTES = {'title', 'alt', 'width', 'height'}
ALLOWED_ATTRIBUTES: _AllowedAttributesDict = {
    **bleach.ALLOWED_ATTRIBUTES,
    '*': ['style', 'class'],
    'a': ['href', 'rel'],
    'img': ['src', *IMG_SAFE_ATTRIBUTES],  # NB: 'filter_img_src' can be used here
}
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'address', 'area',
    'article', 'aside',  # 'audio',
    'b', 'big', 'blockquote', 'br', 'button',
    'canvas', 'caption', 'center', 'cite', 'code', 'col', 'colgroup',
    'command', 'datagrid', 'datalist', 'dd', 'del', 'details', 'dfn',
    'dialog', 'dir', 'div', 'dl', 'dt', 'em', 'event-source', 'fieldset',
    'figcaption', 'figure', 'footer', 'font', 'form', 'header', 'h1',
    'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'input', 'ins',
    'keygen', 'kbd', 'label', 'legend', 'li', 'm', 'map', 'menu', 'meter',
    'multicol', 'nav', 'nextid', 'ol', 'output', 'optgroup', 'option',
    'p', 'pre', 'progress', 'q', 's', 'samp', 'section', 'select',
    'small', 'sound', 'source', 'spacer', 'span', 'strike', 'strong',
    'sub', 'sup', 'table', 'tbody', 'td', 'textarea', 'time', 'tfoot',
    'th', 'thead', 'tr', 'tt', 'u', 'ul', 'var',  # 'video',
    'html', 'head', 'title', 'body',
    # 'style'  # TODO: if we allow <style>, we have to sanitize the inline CSS (it's hard)
]
# TODO: see html5lib: mathml_elements, svg_elements ??

ALLOWED_STYLES = [
    # 'azimuth',
    'background-color',
    'border-bottom-color', 'border-collapse', 'border-color',
    'border-left-color', 'border-right-color', 'border-top-color',
    'clear',
    'color',
    # 'cursor',
    'direction', 'display', 'elevation', 'float',
    'font', 'font-family', 'font-size', 'font-style', 'font-variant', 'font-weight',
    'height', 'letter-spacing', 'line-height', 'overflow',
    # 'pause', 'pause-after', 'pause-before', 'pitch', 'pitch-range', 'richness',
    # 'speak', 'speak-header', 'speak-numeral', 'speak-punctuation', 'speech-rate',
    # 'stress',
    'text-align', 'text-decoration', 'text-indent',
    'unicode-bidi', 'vertical-align',
    # 'voice-family', 'volume',
    'white-space', 'width',
]


def filter_img_src(tag, attr, value):
    if attr in IMG_SAFE_ATTRIBUTES:
        return True

    # XXX: this feature is probably broken (& not used) -- see urls.py
    # TODO: remove the external image feature ??
    if attr == 'src':
        return value.startswith(settings.MEDIA_URL)

    return False


def sanitize_html(html: str, allow_external_img: bool = False) -> str:
    attributes: _AllowedAttributesDict = (
        ALLOWED_ATTRIBUTES
        if allow_external_img else
        {**ALLOWED_ATTRIBUTES, 'img': filter_img_src}
    )

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS, attributes=attributes,
        styles=ALLOWED_STYLES, strip=True,
    )


JSON_ESCAPES = {
    ord('\\'): '\\u005C',
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
    ord('\u2028'): '\\u2028',
    ord('\u2029'): '\\u2029'
}
# Escape every ASCII character with a value less than 32.
# JSON_ESCAPES.update((ord('%c' % z), '\\u%04X' % z) for z in range(32))


def escapejson(value: str) -> str:
    # return mark_safe(force_text(value).translate(JSON_ESCAPES))
    return mark_safe(force_str(value).translate(JSON_ESCAPES))


def strip_html(text: str) -> str:
    """ Removes HTML markups from a string, & replaces HTML entities by unicode.

    THX to:
    http://effbot.org/zone/re-sub.htm#strip-html
    """
    def fix_up(m):
        sub_text = m.group(0)
        startswith = sub_text.startswith

        if startswith('<'):
            return ''  # ignore tags

        if startswith('&'):
            if startswith('&#'):
                try:
                    if startswith('&#x'):
                        return chr(int(sub_text[3:-1], 16))
                    else:
                        return chr(int(sub_text[2:-1]))
                except ValueError:
                    pass
            else:
                entity = html_entities.get(sub_text[1:-1])

                if entity:
                    # if entity.startswith('&#'):
                    #     try:
                    #         return chr(int(entity[2:-1]))
                    #     except ValueError:
                    #         pass
                    # else:
                    #     return entity
                    return entity  # TODO: encode ?

        return sub_text  # Leave as is

    return re.sub(r'(?s)<[^>]*>|&#?\w+;', fix_up, text)
