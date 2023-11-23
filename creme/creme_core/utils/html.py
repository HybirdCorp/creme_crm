################################################################################
#
# Copyright (c) 2015-2024 Hybird
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

from __future__ import annotations

import re
from html.entities import entitydefs as html_entities
from typing import TYPE_CHECKING

import bleach
from bleach.css_sanitizer import CSSSanitizer
from django.conf import settings
from django.utils.encoding import force_str
from django.utils.html import format_html, format_html_join, mark_safe
from django.utils.translation import ngettext

if TYPE_CHECKING:
    from typing import Callable, Dict, Sequence, Union

    AllowedAttributesDict = Dict[str, Union[Sequence[str], Callable[[str, str, str], bool]]]

IMG_SAFE_ATTRIBUTES = {'title', 'alt', 'width', 'height'}
ALLOWED_ATTRIBUTES: AllowedAttributesDict = {
    **bleach.ALLOWED_ATTRIBUTES,
    '*': ['style', 'class'],
    'a': ['href', 'rel'],
    'img': ['src', *IMG_SAFE_ATTRIBUTES],  # NB: 'filter_img_src' can be used here
}
ALLOWED_TAGS = {
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
}
# TODO: see html5lib: mathml_elements, svg_elements ??

ALLOWED_STYLES = {
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
}


def filter_img_src(tag, attr, value):
    if attr in IMG_SAFE_ATTRIBUTES:
        return True

    # XXX: this feature is probably broken (& not used) -- see urls.py
    # TODO: remove the external image feature ??
    if attr == 'src':
        return value.startswith(settings.MEDIA_URL)

    return False


def sanitize_html(html: str, allow_external_img: bool = False) -> str:
    attributes: AllowedAttributesDict = (
        ALLOWED_ATTRIBUTES
        if allow_external_img else
        {**ALLOWED_ATTRIBUTES, 'img': filter_img_src}
    )

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS, attributes=attributes,
        # styles=ALLOWED_STYLES,
        css_sanitizer=CSSSanitizer(allowed_css_properties=ALLOWED_STYLES),
        strip=True,
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
                    return entity  # TODO: encode ?

        return sub_text  # Leave as is

    return re.sub(r'(?s)<[^>]*>|&#?\w+;', fix_up, text)


def render_limited_list(*, items: Sequence, limit: int, render_item=lambda e: str(e)) -> str:
    """Render the content of a Python list as a <ul> node.
    @param items: list to render.
    @param limit: maximum number of elements; a message indicating the list has
           been truncated is displayed if needed.
    @param render_item: a callable which takes an element of the list <items>
           & returns a string.
    @return: An HTML string. A <ul> element is used only if there are more than 1 element.
    """
    if not items:
        return ''

    length = len(items)
    if length == 1:
        return render_item(items[0])

    def rendered_items():
        for item in items[:limit]:
            yield render_item(item)

        extra_count = length - limit
        if extra_count > 0:
            yield format_html(
                '<span class="more-elements">{}</span>',
                ngettext(
                    '{count} more element', '{count} more elements', extra_count,
                ).format(count=extra_count)
            )

    return format_html(
        '<ul class="limited-list">{}</ul>',
        format_html_join('', '<li>{}</li>', ([item] for item in rendered_items())),
    )
