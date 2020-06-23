# -*- coding: utf-8 -*-

# See http://stackoverflow.com/questions/16259923/how-can-i-escape-latex-special-characters-inside-django-templates  # NOQA

################################################################################
#    Copyright (C) 2014 Matt Bierner
#    Copyright (C) 2016-2020 Hybird
#
#    Permission is hereby granted, free of charge, to any person obtaining a
#    copy of this software and associated documentation files (the "Software"),
#    to deal in the Software without restriction, including without limitation
#    the rights touse, copy, modify, merge, publish, distribute, sublicense,
#    and/or sell copies of the Software, and to permit persons to whom the
#    Software is furnished to do so, subject to the following conditions:

#    The above copyright notice and this permission notice shall be included
#    in all copies or substantial portions of the Software.

#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
################################################################################

import re

from django import template

register = template.Library()


@register.filter(name='latex_newline')
def latex_newline(x):
    return x.replace("\n", "\\newline ")


# TODO: replace "<U+200B>" by "\<U+200B>" ?
CONV = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\^{}',
    '\\': r'\textbackslash{}',
    '<': r'\textless',
    '>': r'\textgreater',
}

_LATEX_ESCAPE_RE = None


@register.filter(name='latex_escape')
def latex_escape(x):
    global _LATEX_ESCAPE_RE

    if not x:
        return x

    x = str(x)

    if _LATEX_ESCAPE_RE is None:
        _LATEX_ESCAPE_RE = re.compile(
            '|'.join(
                re.escape(str(key))
                for key in sorted(CONV.keys(), key=lambda item: - len(item))
            )
        )

    return _LATEX_ESCAPE_RE.sub(lambda match: CONV[match.group()], x)
