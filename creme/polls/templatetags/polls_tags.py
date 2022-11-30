################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2022  Hybird
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

import logging

from django import template
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag
def poll_line_condition(nodes, condition):
    # Cache to avoid additional queries (caused by 'condition.source').
    lines_map = getattr(nodes, 'tags_lines_map', None)

    if lines_map is None:
        nodes.tags_lines_map = lines_map = {
            node.id: node
            for node in nodes if not node.is_section
        }

    source = lines_map[condition.source_id]
    answer = source.poll_line_type.decode_condition(condition.raw_answer)

    if isinstance(answer, list):  # TODO: move logic to core.py ???:
        msg_fmt = _('The answer to the question #{number} contains «{answer}».')
        answer = ' / '.join(answer)  # TODO: stringify sub elements ?
    else:
        msg_fmt = _('The answer to the question #{number} is «{answer}».')

    return msg_fmt.format(number=source.number, answer=answer)


@register.simple_tag
def poll_node_number(style, node):
    return style.number(node)


@register.simple_tag
def poll_node_css(style, node):
    return style.css(node)
