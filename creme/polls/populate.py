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

import logging

from django.utils.translation import ugettext as _
from django.conf import settings

from creme.creme_core.models import (HeaderFilterItem, HeaderFilter,
                                     BlockDetailviewLocation, SearchConfigItem)
from creme.creme_core.utils import create_if_needed
from creme.creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme.creme_core.management.commands.creme_populate import BasePopulator

from creme.persons.models import Contact, Organisation

from .models import PollType, PollForm, PollReply, PollCampaign
from .blocks import *


logger = logging.getLogger(__name__)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self, *args, **kwargs):
        create_if_needed(PollType, {'pk': 1}, name=_(u'Survey'))
        create_if_needed(PollType, {'pk': 2}, name=_(u'Monitoring'))
        create_if_needed(PollType, {'pk': 3}, name=_(u'Assessment'))


        hf = HeaderFilter.create(pk='polls-hf_pollform', name=_(u'Form view'), model=PollForm)
        hf.set_items([HeaderFilterItem.build_4_field(model=PollForm, name='name'),
                     ])

        hf = HeaderFilter.create(pk='polls-hf_pollreply', name=_(u'Reply view'), model=PollReply)
        hf.set_items([HeaderFilterItem.build_4_field(model=PollReply, name='name'),
                      HeaderFilterItem.build_4_field(model=PollReply, name='pform'),
                      HeaderFilterItem.build_4_field(model=PollReply, name='person'),
                     ])

        hf = HeaderFilter.create(pk='polls-hf_pollcampaign', name=_(u'Campaign view'), model=PollCampaign)
        hf.set_items([HeaderFilterItem.build_4_field(model=PollCampaign, name='name'),
                      HeaderFilterItem.build_4_field(model=PollCampaign, name='due_date'),
                      HeaderFilterItem.build_4_field(model=PollCampaign, name='segment'),
                     ])


        SearchConfigItem.create_if_needed(PollForm,  ['name'])
        SearchConfigItem.create_if_needed(PollReply, ['name'])

        BlockDetailviewLocation.create(block_id=pform_lines_block.id_,    order=5,   zone=BlockDetailviewLocation.TOP, model=PollForm)
        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=PollForm)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,   order=40,  zone=BlockDetailviewLocation.LEFT,  model=PollForm)
        BlockDetailviewLocation.create(block_id=properties_block.id_,     order=450, zone=BlockDetailviewLocation.LEFT,  model=PollForm)
        BlockDetailviewLocation.create(block_id=relations_block.id_,      order=500, zone=BlockDetailviewLocation.LEFT,  model=PollForm)
        BlockDetailviewLocation.create(block_id=preplies_block.id_,       order=5,   zone=BlockDetailviewLocation.RIGHT, model=PollForm)
        BlockDetailviewLocation.create(block_id=history_block.id_,        order=20,  zone=BlockDetailviewLocation.RIGHT, model=PollForm)

        #TODO: factorise
        BlockDetailviewLocation.create(block_id=preply_lines_block.id_,     order=5,   zone=BlockDetailviewLocation.TOP, model=PollReply)
        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=PollReply)
        BlockDetailviewLocation.create(block_id=customfields_block.id_  ,   order=40,  zone=BlockDetailviewLocation.LEFT,  model=PollReply)
        BlockDetailviewLocation.create(block_id=properties_block.id_,       order=450, zone=BlockDetailviewLocation.LEFT,  model=PollReply)
        BlockDetailviewLocation.create(block_id=relations_block.id_,        order=500, zone=BlockDetailviewLocation.LEFT,  model=PollReply)
        BlockDetailviewLocation.create(block_id=history_block.id_,          order=20,  zone=BlockDetailviewLocation.RIGHT, model=PollReply)

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=PollCampaign)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,      order=40,  zone=BlockDetailviewLocation.LEFT,  model=PollCampaign)
        BlockDetailviewLocation.create(block_id=properties_block.id_,        order=450, zone=BlockDetailviewLocation.LEFT,  model=PollCampaign)
        BlockDetailviewLocation.create(block_id=relations_block.id_,         order=500, zone=BlockDetailviewLocation.LEFT,  model=PollCampaign)
        BlockDetailviewLocation.create(block_id=pcampaign_replies_block.id_, order=5,   zone=BlockDetailviewLocation.RIGHT, model=PollCampaign)
        BlockDetailviewLocation.create(block_id=history_block.id_,           order=20,  zone=BlockDetailviewLocation.RIGHT, model=PollCampaign)

        BlockDetailviewLocation.create(block_id=related_preplies_block.id_, order=500, zone=BlockDetailviewLocation.RIGHT,  model=Contact)
        BlockDetailviewLocation.create(block_id=related_preplies_block.id_, order=500, zone=BlockDetailviewLocation.RIGHT,  model=Organisation)

        if 'creme.assistants' in settings.INSTALLED_APPS:
            logger.info('Assistants app is installed => we use the assistants blocks on detail view')

            from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in (PollForm, PollReply, PollCampaign):
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)
