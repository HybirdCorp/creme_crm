# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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
from creme.creme_core.gui import creme_menu, button_registry, block_registry, icon_registry, bulk_update_registry

from .models import EmailCampaign, MailingList, EmailTemplate, EntityEmail, _Email
from .blocks import blocks_list, EntityEmailBlock
from .buttons import entityemail_link_button


creme_registry.register_entity_models(EmailCampaign, MailingList, EmailTemplate, EntityEmail)
creme_registry.register_app('emails', _(u'Emails'), '/emails')

reg_item = creme_menu.register_app ('emails', '/emails/').register_item
reg_item('/emails/',                 _(u'Portal of emails'),                   'emails')
reg_item('/emails/campaigns' ,       _(u'All campaigns'),                      'emails')
reg_item('/emails/campaign/add',     EmailCampaign.creation_label,             'emails.add_emailcampaign')
reg_item('/emails/mailing_lists',    _(u'All mailing lists'),                  'emails')
reg_item('/emails/mailing_list/add', MailingList.creation_label,               'emails.add_mailinglist')
reg_item('/emails/templates',        _(u'All email templates'),                'emails')
reg_item('/emails/template/add',     EmailTemplate.creation_label,             'emails.add_emailtemplate')
reg_item('/emails/mails',            _(u'All emails'),                         'emails')
reg_item('/emails/synchronization',  _(u'Synchronization of incoming emails'), 'emails')

button_registry.register(entityemail_link_button)

block_registry.register_4_model(EntityEmail, EntityEmailBlock())
block_registry.register(*blocks_list)

reg_icon = icon_registry.register
reg_icon(EntityEmail,   'images/email_%(size)s.png')
reg_icon(MailingList,   'images/email_%(size)s.png')
reg_icon(EmailCampaign, 'images/email_%(size)s.png')
reg_icon(EmailTemplate, 'images/email_%(size)s.png')

bulk_update_registry.register(
    (EmailTemplate, []),
    (_Email,        ['reads', 'status', 'recipient', 'body_html', 'body', 'sending_date',
                     'reception_date', 'signature', 'attachments', 'subject',
                     'sender']),#TODO: Remove bulk update instead of that ?
)

