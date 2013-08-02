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

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import creme_menu, block_registry, icon_registry, bulk_update_registry

from .models import PollForm, PollReply, PollCampaign
from .blocks import block_list


creme_registry.register_app('polls', _(u'Polls'), '/polls')
creme_registry.register_entity_models(PollForm, PollReply, PollCampaign)

reg_item = creme_menu.register_app('polls', '/polls/').register_item
reg_item('/polls/',               _(u'Portal of polls'),       'polls')
reg_item('/polls/poll_forms',     _(u'All forms'),             'polls')
reg_item('/polls/poll_form/add',  PollForm.creation_label,     'polls.add_pollform')
reg_item('/polls/poll_replies',   _(u'All replies'),           'polls')
reg_item('/polls/poll_reply/add', PollReply.creation_label,    'polls.add_pollreply')
reg_item('/polls/campaigns',      _(u'All campaigns'),         'polls')
reg_item('/polls/campaign/add',   PollCampaign.creation_label, 'polls.add_pollcampaign')

block_registry.register(*block_list)

reg_icon = icon_registry.register
reg_icon(PollForm,     'images/poll_%(size)s.png')
reg_icon(PollReply,    'images/poll_%(size)s.png')
reg_icon(PollCampaign, 'images/poll_%(size)s.png')

#TODO: remove when BulkUpdate manages correctly FK on CremeEntity (right field/widget) (see test_regular_field09)
bulk_update_registry.register(
    (PollReply, ['campaign', 'person']),
)
