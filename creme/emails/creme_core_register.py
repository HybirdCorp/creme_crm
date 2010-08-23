# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry

from emails.models import EmailCampaign, MailingList, EmailTemplate
from emails.blocks import *


creme_registry.register_entity_models(EmailCampaign, MailingList, EmailTemplate)
creme_registry.register_app ('emails', _(u'Courriels'), '/emails')

creme_menu.register_app ('emails', '/emails/', "Courriels et Campagnes")
reg_menu = creme_menu.register_menu
reg_menu('emails', '/emails/campaigns' ,       'Lister les campagnes' )
reg_menu('emails', '/emails/campaign/add',     'Ajouter une campagne')
reg_menu('emails', '/emails/mailing_lists',    'Lister les listes de diffusion')
reg_menu('emails', '/emails/mailing_list/add', 'Ajouter une liste de diffusion')
reg_menu('emails', '/emails/templates',        'Lister les patrons de courriel')
reg_menu('emails', '/emails/template/add',     'Ajouter un patron de courriel')
reg_menu('emails', '/emails/synchronization',  'Synchronisation des emails externes')

block_registry.register(mailing_lists_block, recipients_block, contacts_block, organisations_block,
                        child_lists_block, parent_lists_block, attachments_block, sendings_block,
                        mails_block, mails_history_block, mail_waiting_sync_block, mail_spam_sync_block)
