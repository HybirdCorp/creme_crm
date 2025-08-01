################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020-2025  Hybird
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
#############################################################################

from django.template import Library
from django.utils.functional import partition

from creme.creme_core.forms.base import LAYOUT_DUAL_FIRST, LAYOUT_REGULAR

register = Library()


@register.filter
def form_gather_blocks_for_layout(form_blocks):
    sections = []
    i = 0
    form_blocks = [*form_blocks]
    length = len(form_blocks)

    while i < length:
        block = form_blocks[i]

        if block.layout == LAYOUT_REGULAR:
            regular_section = [block]
            i += 1

            while i < length and form_blocks[i].layout == LAYOUT_REGULAR:
                regular_section.append(form_blocks[i])
                i += 1

            sections.append(('regular', regular_section))
        else:  # LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
            dual_section = [block]
            i += 1

            while i < length and form_blocks[i].layout != LAYOUT_REGULAR:
                dual_section.append(form_blocks[i])
                i += 1

            sections.append((
                'dual',
                partition(
                    lambda b: b.layout != LAYOUT_DUAL_FIRST,
                    dual_section,
                ),
            ))

    return sections
