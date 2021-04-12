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

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from creme import persons, polls
from creme.creme_core.gui.bricks import (
    Brick,
    BrickDependencies,
    QuerysetBrick,
    SimpleBrick,
)

from .models import PollFormLine, PollReplyLine
from .utils import NodeStyle, ReplySectionTree, SectionTree

PollCampaign = polls.get_pollcampaign_model()
PollForm     = polls.get_pollform_model()
PollReply    = polls.get_pollreply_model()


class PollFormBarHatBrick(SimpleBrick):
    template_name = 'polls/bricks/pform-hat-bar.html'


class PollFormLinesBrick(Brick):
    id_ = Brick.generate_id('polls', 'pollform_lines')
    verbose_name = _('Form lines')
    dependencies = (PollFormLine,)
    template_name = 'polls/bricks/pform-lines.html'
    target_ctypes = (PollForm,)

    @staticmethod
    def _build_title(nodes):
        section_count = 0
        question_count = 0

        for node in nodes:
            if node.is_section:
                section_count += 1
            else:
                question_count += 1

        def question_label():
            return ngettext(
                '{count} Question',
                '{count} Questions',
                question_count,
            ).format(count=question_count)

        def section_label():
            return ngettext(
                '{count} Section',
                '{count} Sections',
                section_count,
            ).format(count=section_count)

        if section_count and question_count:
            # TODO: unit test
            return gettext('{questions} and {sections}').format(
                questions=question_label(),
                sections=section_label(),
            )
        elif section_count:
            return section_label()
        elif question_count:
            return question_label()

        return gettext('Questions')

    def detailview_display(self, context):
        pform = context['object']
        nodes = SectionTree(pform)

        PollFormLine.populate_conditions([node for node in nodes if not node.is_section])

        return self._render(self.get_template_context(
            context,
            nodes=nodes,
            title=self._build_title(nodes),
            style=NodeStyle(),
        ))


class PollReplyLinesBrick(Brick):
    id_ = Brick.generate_id('polls', 'pollreply_lines')
    verbose_name = _('Reply lines')
    dependencies = (PollReplyLine,)
    template_name = 'polls/bricks/preply-lines.html'
    target_ctypes = (PollReply,)

    def detailview_display(self, context):
        preply = context['object']
        nodes = ReplySectionTree(preply)

        nodes.set_conditions_flags()

        return self._render(self.get_template_context(
            context,
            nodes=nodes,
            style=NodeStyle(),
        ))


class PollRepliesBrick(QuerysetBrick):
    id_ = QuerysetBrick.generate_id('polls', 'poll_replies')
    verbose_name = _('Form replies')

    # PollFormLine : the 'New' button appears only if there is at least one line.
    dependencies = (PollReply, PollFormLine)

    template_name = 'polls/bricks/preplies.html'
    target_ctypes = (PollForm,)

    def detailview_display(self, context):
        pform = context['object']

        return self._render(self.get_template_context(
            context,
            PollReply.objects.filter(pform=pform, is_deleted=False),
            # TODO: reuse nodes (PollFormLinesBlock) to avoid a query
            propose_creation=pform.lines.exists(),
        ))


class _RelatedRepliesBrick(QuerysetBrick):
    dependencies: BrickDependencies = (PollReply,)
    verbose_name = _('Related form replies')

    def _get_replies(self, pk):
        raise NotImplementedError

    def detailview_display(self, context):
        pk = context['object'].id

        return self._render(self.get_template_context(
            context,
            self._get_replies(pk).filter(is_deleted=False),
            propose_creation=True,
        ))


class PersonPollRepliesBrick(_RelatedRepliesBrick):
    id_ = _RelatedRepliesBrick.generate_id('polls', 'person_replies')
    template_name = 'polls/bricks/person-preplies.html'
    target_ctypes = (persons.get_contact_model(), persons.get_organisation_model())

    def _get_replies(self, pk):
        return PollReply.objects.filter(person=pk)


class PollCampaignRepliesBrick(_RelatedRepliesBrick):
    id_ = _RelatedRepliesBrick.generate_id('polls', 'pcampaign_replies')
    # PollCampaign: expected_count can be edited
    dependencies = (*_RelatedRepliesBrick.dependencies, PollCampaign)
    template_name = 'polls/bricks/campaign-preplies.html'
    target_ctypes = (PollCampaign,)

    def _get_replies(self, pk):
        return PollReply.objects.filter(campaign=pk)
