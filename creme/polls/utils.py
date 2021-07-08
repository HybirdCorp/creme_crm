# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2012-2021  Hybird
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

from collections import Counter, defaultdict
from itertools import count

from creme.creme_core.utils import int_2_roman

from . import get_pollform_model, get_pollreply_model
from .models import (
    PollFormLine,
    PollFormSection,
    PollReplyLine,
    PollReplySection,
)

# TODO move to core.section_tree.py ??

_CLASS_MAPPING = {
    get_pollform_model():  ('pform',  PollFormSection, PollFormLine),
    get_pollreply_model(): ('preply', PollReplySection, PollReplyLine),
}


class NodeStyle:  # TODO: configurable style stored in DB
    ELEMENTS = {
        'COLOR': {
            'LINE':      '',  # Use normal brick line color
            'SECTION_0': 'BDD8E4',
            'SECTION_1': 'D8E5EB',
            'SECTION':   'D8E5EB',  # Default
        },
        'NUMBER': {
            'LINE':      str,
            'SECTION_0': int_2_roman,
            'SECTION_1': str,
            'SECTION':   str,  # Default
        },
    }

    def _get_element(self, type, node, default):
        get = self.ELEMENTS[type].get

        if node.is_section:
            element = get(f'SECTION_{node.deep}') or get('SECTION', default)
        else:
            element = get('LINE', default)

        return element

    def number(self, node):
        return self._get_element('NUMBER', node, str)(node.number)

    def css(self, node):
        color = self._get_element('COLOR', node, '')

        return f'background-color: #{color};' if color else ''


class SectionTree:
    def __init__(self, pobj):
        attr_name, section_model, line_model = _CLASS_MAPPING[pobj.__class__]

        self._nodes = nodes = []
        kwargs = {attr_name: pobj.id}

        sections_map = defaultdict(list)
        # TODO: sadly this cause an extra query to get the related CremeEntity (check again)...
        #   for section in pform.sections.all():
        for section in section_model.objects.filter(**kwargs):
            section.is_section = True
            section.deep = 0
            section.number = 1
            sections_map[section.parent_id].append(section)

        lines_map = defaultdict(list)
        gen_number = count(1).__next__
        # for line in pform.lines.all(): # TODO: idem
        for line in line_model.objects.filter(**kwargs):
            line.is_section = False
            line.deep = 0
            line.number = (
                gen_number()
                if line.poll_line_type.editable and not getattr(line, 'disabled', False)
                else None
            )
            lines_map[line.section_id].append(line)

        nodes.extend(lines_map[None])
        self._build_nodes(nodes.append, None, sections_map, lines_map, 0)

    def _build_nodes(self, nodes_append, parent_section_id, sections_map, lines_map, deep):
        deeper = deep + 1
        parent_has_line = False

        for i, section in enumerate(sections_map[parent_section_id], start=1):
            section.deep = deep
            section.number = i
            nodes_append(section)

            lines = lines_map[section.id]

            for line in lines:
                line.deep = deeper
                nodes_append(line)

            section.has_line = has_line = self._build_nodes(
                nodes_append, section.id, sections_map, lines_map, deeper
            ) or bool(lines)
            parent_has_line = parent_has_line or has_line

        return parent_has_line

    def __iter__(self):
        return iter(self._nodes)

    def find_line(self, line_id):
        for node in self._nodes:
            if not node.is_section and node.id == line_id:
                return node

        raise KeyError(line_id)


class ReplySectionTree(SectionTree):
    def __init__(self, preply):
        super().__init__(preply)
        PollReplyLine.populate_conditions([
            node for node in self if not node.is_section
        ])

    def conditions_are_met(self, line_node):
        conditions = line_node.get_conditions()

        if not conditions:
            return True

        op = any if line_node.conds_use_or else all
        find_line = self.find_line

        return op(cond.is_met(find_line(cond.source_id)) for cond in conditions)

    def get_previous_answered_question(self, from_node):
        previous = None
        from_node_id = from_node.id

        for node in self:
            if not node.is_section:
                if node.id == from_node_id:
                    return previous
                if node.raw_answer is not None or not node.applicable:
                    previous = node

    @property
    def next_question_to_answer(self):
        conditions_are_met = self.conditions_are_met

        for node in self:
            if (
                not node.is_section
                and node.raw_answer is None
                and node.applicable
                and conditions_are_met(node)
            ):
                return node

    def set_conditions_flags(self):
        conditions_are_met = self.conditions_are_met

        for node in self:
            if not node.is_section:
                node.conditions_are_met = conditions_are_met(node)


class StatsTree(SectionTree):
    def __init__(self, pform):
        super().__init__(pform)
        flines = [node for node in self if not node.is_section]
        replies_map = defaultdict(list)

        for rline in PollReplyLine.objects.filter(pform_line__in=flines):
            replies_map[rline.pform_line_id].append(rline)

        for fline in flines:
            stats = Counter()
            total = 0

            for rline in replies_map[fline.id]:
                rline_stats = rline.stats or []

                for choice_label, choice_count in rline_stats:
                    total += choice_count
                    stats[choice_label] += choice_count

            fline.answer_stats = [
                (
                    stat_label,
                    stat_count,
                    round(float(stat_count * 100) / float(total), 2),
                ) for stat_label, stat_count in stats.items()
            ] if total > 0 else []
