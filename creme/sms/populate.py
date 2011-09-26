# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from logging import info

from django.utils.translation import ugettext as _
from django.conf import settings

from creme_core.models import SearchConfigItem, HeaderFilterItem, HeaderFilter, BlockDetailviewLocation
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.management.commands.creme_populate import BasePopulator

from sms.models import MessagingList, SMSCampaign, MessageTemplate
from sms.blocks import messaging_lists_block, recipients_block, contacts_block, messages_block, sendings_block


class Populator(BasePopulator):
    dependencies = ['creme_core']

    def populate(self, *args, **kwargs):
        hf = HeaderFilter.create(pk='sms-hf_mlist', name=_(u'Messaging list view'), model=MessagingList)
        hf.set_items([HeaderFilterItem.build_4_field(model=MessagingList, name='name')])

        hf = HeaderFilter.create(pk='sms-hf_campaign', name=_(u'Campaign view'), model=SMSCampaign)
        hf.set_items([HeaderFilterItem.build_4_field(model=SMSCampaign, name='name')])

        hf = HeaderFilter.create(pk='sms-hf_template', name=_(u'Message template view'), model=MessageTemplate)
        hf.set_items([HeaderFilterItem.build_4_field(model=MessageTemplate, name='name')])

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=SMSCampaign)
        BlockDetailviewLocation.create(block_id=sendings_block.id_,        order=2,   zone=BlockDetailviewLocation.TOP,   model=SMSCampaign)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,    order=40,  zone=BlockDetailviewLocation.LEFT,  model=SMSCampaign)
        BlockDetailviewLocation.create(block_id=messaging_lists_block.id_, order=50,  zone=BlockDetailviewLocation.LEFT,  model=SMSCampaign)
        BlockDetailviewLocation.create(block_id=properties_block.id_,      order=450, zone=BlockDetailviewLocation.LEFT,  model=SMSCampaign)
        BlockDetailviewLocation.create(block_id=relations_block.id_,       order=500, zone=BlockDetailviewLocation.LEFT,  model=SMSCampaign)
        BlockDetailviewLocation.create(block_id=history_block.id_,         order=20,  zone=BlockDetailviewLocation.RIGHT, model=SMSCampaign)

        BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=MessagingList)
        BlockDetailviewLocation.create(block_id=customfields_block.id_,    order=40,  zone=BlockDetailviewLocation.LEFT,  model=MessagingList)
        BlockDetailviewLocation.create(block_id=recipients_block.id_,      order=50,  zone=BlockDetailviewLocation.LEFT,  model=MessagingList)
        BlockDetailviewLocation.create(block_id=contacts_block.id_,        order=55,  zone=BlockDetailviewLocation.LEFT,  model=MessagingList)
        BlockDetailviewLocation.create(block_id=properties_block.id_,      order=450, zone=BlockDetailviewLocation.LEFT,  model=MessagingList)
        BlockDetailviewLocation.create(block_id=relations_block.id_,       order=500, zone=BlockDetailviewLocation.LEFT,  model=MessagingList)
        BlockDetailviewLocation.create(block_id=history_block.id_,         order=20,  zone=BlockDetailviewLocation.RIGHT, model=MessagingList)

        if 'assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail views')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in (SMSCampaign, MessagingList):
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

        SearchConfigItem.create_if_needed(SMSCampaign, ['name'])
        SearchConfigItem.create_if_needed(MessagingList, ['name'])
