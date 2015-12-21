# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

import bleach

from django.conf import settings


IMG_SAFE_ATTRIBUTES = {'title', 'alt', 'width', 'height'}
ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES,
                          **{'*': ['style', 'class'],
                             'a': ['href', 'rel'],
                             'img': ['src'] + list(IMG_SAFE_ATTRIBUTES),  # NB: 'filter_img_src' can be used here
                            }
                         )
ALLOWED_TAGS = ['a', 'abbr', 'acronym', 'address', 'area',
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

ALLOWED_STYLES = [#'azimuth',
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


def filter_img_src(name, value):
    if name in IMG_SAFE_ATTRIBUTES:
        return True

    if name == 'src':
        return value.startswith(settings.MEDIA_URL)

    return False


def sanitize_html(html, allow_external_img=False):
    attributes = ALLOWED_ATTRIBUTES if allow_external_img else \
                 dict(ALLOWED_ATTRIBUTES, img=filter_img_src)

    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=attributes,
                        styles=ALLOWED_STYLES, strip=True,
                       )
