# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2017  Hybird
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

from json import dumps as json_dump
import logging, warnings

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from creme.polls.core import PollLineType


logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag
def print_line_condition(nodes, condition):  # TODO: rename 'poll_line_condition'
    # Cache to avoid additional queries (caused by 'condition.source').
    lines_map = getattr(nodes, 'tags_lines_map', None)

    if lines_map is None:
        nodes.tags_lines_map = lines_map = {node.id: node for node in nodes if not node.is_section}

    source = lines_map[condition.source_id]
    answer = source.poll_line_type.decode_condition(condition.raw_answer)

    if isinstance(answer, list):  # TODO: move logic to core.py ???:
        msg_fmt = _(u'The answer to the question #%(number)s contains «%(answer)s».')
        answer = u' / '.join(answer)  # TODO: stringify sub elements ?
    else:
        msg_fmt = _(u'The answer to the question #%(number)s is «%(answer)s».')

    return msg_fmt % {'number': source.number,
                      'answer': answer,
                     }


@register.simple_tag
def print_node_number(style, node):  # TODO: rename 'poll_node_number'
    return style.number(node)


@register.simple_tag
def print_node_css(style, node):  # TODO: rename 'poll_node_css'
    return style.css(node)


@register.inclusion_tag('polls/templatetags/stats_pollreply_chart.html', takes_context=True)
def print_node_chart(context, node, diameter=100):
    warnings.warn('The templatetag {% print_node_chart %} is deprecated ; '
                  'use {% poll_stats_chart %} instead.',
                  DeprecationWarning
                 )

    data = []
    legends = []
    max_legend_length = 0
    count = 0

    for answer, stat, percent in node.answer_stats:
        label = escape(unicode(answer))
        fmt = u'%3d %% - %s' if percent.is_integer() else u'%3.2f %% - %s'
        legend = fmt % (percent, label)
        max_legend_length = max(max_legend_length, len(legend))
        count += 1

        data.append((label, stat))
        legends.append(legend)

    context.update({
                'chart_data':     mark_safe(json_dump([data])),
                'chart_labels':   mark_safe(json_dump(legends)),
                'chart_diameter': diameter,
                'chart_width':    max(diameter * 2 + 50, diameter + max_legend_length * 9),
                'chart_height':   max(diameter + 75, 80 + 25 * count),
            })

    return context


@register.simple_tag
def poll_stats_chart(node):
    try:
        if node.type == PollLineType.BOOL:
            chartpath = 'polls/templatetags/plots/boolean.html'
            data = [[[percent, 1, u'%s − %s %%' % (unicode(answer), percent)]]
                        for answer, _stat, percent in node.answer_stats
                   ]
        else:
            chartpath = 'polls/templatetags/plots/number.html'
            data = [[[percent, unicode(answer)] for answer, _stat, percent in node.answer_stats]
                   ]

        context = {
            'node': node,
            'data': mark_safe(json_dump(data)),
            'count': len(node.answer_stats),
        }

        return template.loader.render_to_string(chartpath, context)
    except Exception:
        logger.exception('An error occured in {% poll_stats_chart %}')

        return _(u'[An error occurred]')
