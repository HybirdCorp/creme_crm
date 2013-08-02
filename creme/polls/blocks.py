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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.gui.block import Block, QuerysetBlock

from creme.persons.models import Contact, Organisation

from .models import (PollCampaign, PollForm, PollFormLine, PollReply,
                     PollReplyLine, PollFormSection)
from .utils import SectionTree, ReplySectionTree, NodeStyle


get_ct = ContentType.objects.get_for_model
_CT_REPLY = get_ct(PollReply)
_CT_FLINE_ID = get_ct(PollFormLine).id
_CT_SECTION_ID = get_ct(PollFormSection).id


class PollFormLinesBlock(Block):
    id_           = Block.generate_id('polls', 'pollform_lines')
    dependencies  = (PollFormLine,)
    verbose_name  = _(u'Form lines')
    template_name = 'polls/templatetags/block_pollform_lines.html'
    target_ctypes = (PollForm,)

    def detailview_display(self, context):
        pform = context['object']
        nodes = SectionTree(pform)

        PollFormLine.populate_conditions([node for node in nodes if not node.is_section])

        return self._render(self.get_block_template_context(
                        context,
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pform.pk),
                        nodes=nodes,
                        style=NodeStyle(),
                        line_ct_id=_CT_FLINE_ID,
                        section_ct_id=_CT_SECTION_ID,
                       )
                    )


class PollReplyLinesBlock(Block):
    id_           = Block.generate_id('polls', 'pollreply_lines')
    dependencies  = (PollReplyLine,)
    verbose_name  = _(u'Reply lines')
    template_name = 'polls/templatetags/block_pollreply_lines.html'
    target_ctypes = (PollReply,)

    def detailview_display(self, context):
        preply = context['object']
        nodes = ReplySectionTree(preply)

        nodes.set_conditions_flags()

        return self._render(self.get_block_template_context(
                        context,
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, preply.pk),
                        nodes=nodes,
                        style=NodeStyle(),
                       )
                    )


class PollRepliesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('polls', 'poll_replies')
    dependencies  = (PollReply, PollFormLine) #PollFormLine : the 'New' button appears only if there is at least one line.
    verbose_name  = _(u'Form replies')
    template_name = 'polls/templatetags/block_preplies.html'
    target_ctypes = (PollForm,)

    def detailview_display(self, context):
        pform = context['object']

        return self._render(self.get_block_template_context(
                        context,
                        PollReply.objects.filter(pform=pform),
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pform.pk),
                        ct_reply=_CT_REPLY,
                        propose_creation=pform.lines.exists(), #TODO: reuse nodes (PollFormLinesBlock) to avoid a query
                       )
                    )


class _RelatedRepliesBlock(QuerysetBlock):
    dependencies  = (PollReply,)
    verbose_name  = _(u'Related form replies')

    def _get_replies(self, pk):
        raise NotImplementedError

    def detailview_display(self, context):
        pk = context['object'].id

        return self._render(self.get_block_template_context(
                        context,
                        self._get_replies(pk),
                        update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                        ct_reply=_CT_REPLY,
                        propose_creation=True,
                       )
                    )


class PersonPollRepliesBlock(_RelatedRepliesBlock):
    id_           = _RelatedRepliesBlock.generate_id('polls', 'person_replies')
    template_name = 'polls/templatetags/block_person_preplies.html'
    target_ctypes = (Contact, Organisation)

    def _get_replies(self, pk):
        return PollReply.objects.filter(person=pk)


class PollCampaignRepliesBlock(_RelatedRepliesBlock):
    id_           = _RelatedRepliesBlock.generate_id('polls', 'pcampaign_replies')
    dependencies  = _RelatedRepliesBlock.dependencies + (PollCampaign,) #PollCampaign: expected_count can be edited
    template_name = 'polls/templatetags/block_campaign_preplies.html'
    target_ctypes = (PollCampaign,)

    def _get_replies(self, pk):
        return PollReply.objects.filter(campaign=pk)



pform_lines_block       = PollFormLinesBlock()
preply_lines_block      = PollReplyLinesBlock()
preplies_block          = PollRepliesBlock()
related_preplies_block  = PersonPollRepliesBlock()
pcampaign_replies_block = PollCampaignRepliesBlock()

block_list = (
        pform_lines_block,
        preply_lines_block,
        preplies_block,
        related_preplies_block,
        pcampaign_replies_block,
    )
