# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from creme import polls
from creme.creme_core.gui import menu

PollForm = polls.get_pollform_model()
PollReply = polls.get_pollreply_model()
PollCampaign = polls.get_pollcampaign_model()


class PollFormsEntry(menu.ListviewEntry):
    id = 'polls-poll_forms'
    model = PollForm


class PollRepliesEntry(menu.ListviewEntry):
    id = 'polls-poll_replies'
    model = PollReply


class PollCampaignsEntry(menu.ListviewEntry):
    id = 'polls-poll_campaigns'
    model = PollCampaign


class PollFormCreationEntry(menu.CreationEntry):
    id = 'polls-create_poll_form'
    model = PollForm


class PollReplyCreationEntry(menu.CreationEntry):
    id = 'polls-create_poll_reply'
    model = PollReply


class PollCampaignCreationEntry(menu.CreationEntry):
    id = 'polls-create_poll_campaign'
    model = PollCampaign
