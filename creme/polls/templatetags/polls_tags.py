# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2013  Hybird
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

from django.template import Library
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.translation import ugettext as _


register = Library()

@register.simple_tag
def print_line_condition(nodes, condition):
    lines_map = getattr(nodes, 'tags_lines_map', None) #cache to avoid additionnal queries (caused by 'condition.source').

    if lines_map is None:
        nodes.tags_lines_map = lines_map = dict((node.id, node) for node in nodes if not node.is_section)

    source = lines_map[condition.source_id]
    answer = source.poll_line_type.decode_condition(condition.raw_answer)

    if isinstance(answer, list): #TODO: move logic to core.py ???:
        msg_fmt = _(u'The answer to the question #%(number)s contains «%(answer)s».')
        answer = u' / '.join(answer) #TODO: stringify sub elements ?
    else:
        msg_fmt = _(u'The answer to the question #%(number)s is «%(answer)s».')

    return msg_fmt % {'number': source.number,
                      'answer': answer,
                     }

@register.simple_tag
def print_node_number(style, node):
    return style.number(node)

@register.simple_tag
def print_node_css(style, node):
    return style.css(node)

@register.inclusion_tag('polls/templatetags/stats_pollreply_chart.html', takes_context=True)
def print_node_chart(context, node, diameter=100):
    data = []
    legends = []
    max_legend_length = 0
    count = 0

    #if node.answer_stats:
    for answer, stat, percent in node.answer_stats:
        label = escape(unicode(answer))
        fmt = u'%3d %% - %s' if percent.is_integer() else u'%3.2f %% - %s'
        legend = fmt % (percent, label)
        max_legend_length = max(max_legend_length, len(legend))
        count += 1

        data.append((label, stat))
        legends.append(legend)
    #else: #todo: should be useless --> remove
        #label = _('No available answer')
        #legend = u'100 %% - %s' % label
        #max_legend_length = len(legend)
        #count = 1

        #data = [[label, 1]]
        #legends = [legend]

    encode = JSONEncoder().encode
    context.update({
                'chart_data':     mark_safe(encode([data])),
                'chart_labels':   mark_safe(encode(legends)),
                'chart_diameter': diameter,
                'chart_width':    max(diameter * 2 + 50, diameter + max_legend_length * 9),
                'chart_height':   max(diameter + 75, 80 + 25 * count),
            })

    return context
