# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.gui import creme_menu, block_registry, icon_registry, bulk_update_registry
from creme.creme_core.registry import creme_registry

from . import get_smscampaign_model, get_messaginglist_model, get_messagetemplate_model
#from .models import SMSCampaign, MessagingList, MessageTemplate
from .blocks import messaging_lists_block, recipients_block, contacts_block, messages_block, sendings_block


SMSCampaign     = get_smscampaign_model()
MessagingList   = get_messaginglist_model()
MessageTemplate = get_messagetemplate_model()

creme_registry.register_entity_models(SMSCampaign, MessagingList, MessageTemplate)
creme_registry.register_app('sms', _(u'SMS'), '/sms')

reg_item = creme_menu.register_app('sms', '/sms/').register_item
reg_item('/sms/',                   _(u'Portal of SMS'),            'sms')
#reg_item('/sms/campaigns' ,         _(u'All campaigns'),            'sms')
#reg_item('/sms/campaign/add',       SMSCampaign.creation_label,     'sms.add_smscampaign')
#reg_item('/sms/messaging_lists',    _(u'All messaging lists'),      'sms')
#reg_item('/sms/messaging_list/add', MessagingList.creation_label,   'sms.add_messaginglist')
#reg_item('/sms/templates',          _(u'All message templates'),    'sms')
#reg_item('/sms/template/add',       MessageTemplate.creation_label, 'sms.add_messagetemplate')
reg_item(reverse('sms__list_campaigns'),   _(u'All campaigns'),            'sms')
reg_item(reverse('sms__create_campaign'),  SMSCampaign.creation_label,      build_creation_perm(SMSCampaign))
reg_item(reverse('sms__list_mlists'),      _(u'All messaging lists'),      'sms')
reg_item(reverse('sms__create_mlist'),     MessagingList.creation_label,    build_creation_perm(MessagingList))
reg_item(reverse('sms__list_templates'),  _(u'All message templates'),    'sms')
reg_item(reverse('sms__create_template'), MessageTemplate.creation_label,  build_creation_perm(MessageTemplate))

block_registry.register(messaging_lists_block, recipients_block, contacts_block, messages_block, sendings_block)

reg_icon = icon_registry.register
reg_icon(SMSCampaign,     'images/sms_%(size)s.png')
reg_icon(MessagingList,   'images/sms_%(size)s.png')
reg_icon(MessageTemplate, 'images/sms_%(size)s.png')

bulk_update_registry.register(SMSCampaign, exclude=('lists',))
