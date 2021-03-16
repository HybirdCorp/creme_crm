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

from creme import sms
from creme.creme_core.gui import menu

SMSCampaign = sms.get_smscampaign_model()
MessagingList = sms.get_messaginglist_model()
MessageTemplate = sms.get_messagetemplate_model()


class SMSCampaignsEntry(menu.ListviewEntry):
    id = 'sms-campaigns'
    model = SMSCampaign


class MessagingListsEntry(menu.ListviewEntry):
    id = 'sms-messaging_lists'
    model = MessagingList


class MessageTemplatesEntry(menu.ListviewEntry):
    id = 'sms-message_templates'
    model = MessageTemplate


class SMSCampaignCreationEntry(menu.CreationEntry):
    id = 'sms-create_campaign'
    model = SMSCampaign


class MessagingListCreationEntry(menu.CreationEntry):
    id = 'sms-create_messaging_list'
    model = MessagingList


class MessageTemplateCreationEntry(menu.CreationEntry):
    id = 'sms-create_message_template'
    model = MessageTemplate
