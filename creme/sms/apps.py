# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class SMSConfig(CremeAppConfig):
    name = 'creme.sms'
    verbose_name = _(u'SMS')
    dependencies = ['creme.persons']

    def all_apps_ready(self):
        from . import get_smscampaign_model, get_messaginglist_model, get_messagetemplate_model

        self.SMSCampaign     = get_smscampaign_model()
        self.MessagingList   = get_messaginglist_model()
        self.MessageTemplate = get_messagetemplate_model()
        super(SMSConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('sms', _(u'SMS'), '/sms')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.SMSCampaign,
                                              self.MessagingList,
                                              self.MessageTemplate,
                                             )

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm

        SMSCampaign     = self.SMSCampaign
        MessagingList   = self.MessagingList
        MessageTemplate = self.MessageTemplate

        reg_item = creme_menu.register_app('sms', '/sms/').register_item
        reg_item('/sms/',                         _(u'Portal of SMS'),            'sms')
        reg_item(reverse('sms__list_campaigns'),  _(u'All campaigns'),            'sms')
        reg_item(reverse('sms__create_campaign'), SMSCampaign.creation_label,     build_creation_perm(SMSCampaign))
        reg_item(reverse('sms__list_mlists'),     _(u'All messaging lists'),      'sms')
        reg_item(reverse('sms__create_mlist'),    MessagingList.creation_label,   build_creation_perm(MessagingList))
        reg_item(reverse('sms__list_templates'),  _(u'All message templates'),    'sms')
        reg_item(reverse('sms__create_template'), MessageTemplate.creation_label, build_creation_perm(MessageTemplate))

    def register_blocks(self, block_registry):
        from .blocks import (messaging_lists_block, recipients_block, contacts_block,
                messages_block, sendings_block)

        block_registry.register(messaging_lists_block, recipients_block,
                                contacts_block, messages_block, sendings_block,
                               )

    def register_bulk_update(self, bulk_update_registry):
        bulk_update_registry.register(self.SMSCampaign, exclude=('lists',))

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.SMSCampaign,     'images/sms_%(size)s.png')
        reg_icon(self.MessagingList,   'images/sms_%(size)s.png')
        reg_icon(self.MessageTemplate, 'images/sms_%(size)s.png')

