################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2022  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme import emails
from creme.creme_core.gui import menu

EmailCampaign = emails.get_emailcampaign_model()
MailingList = emails.get_mailinglist_model()
EmailTemplate = emails.get_emailtemplate_model()


class EmailCampaignsEntry(menu.ListviewEntry):
    id = 'emails-campaigns'
    model = EmailCampaign


class MailingListsEntry(menu.ListviewEntry):
    id = 'emails-mailing_lists'
    model = MailingList


class EmailTemplatesEntry(menu.ListviewEntry):
    id = 'emails-email_templates'
    model = EmailTemplate


class EntityEmailsEntry(menu.ListviewEntry):
    id = 'emails-emails'
    model = emails.get_entityemail_model()


class EmailCampaignCreationEntry(menu.CreationEntry):
    id = 'emails-create_campaign'
    model = EmailCampaign


class MailingListCreationEntry(menu.CreationEntry):
    id = 'emails-create_mailing_list'
    model = MailingList


class EmailTemplateCreationEntry(menu.CreationEntry):
    id = 'emails-create_email_template'
    model = EmailTemplate


class EmailSyncEntry(menu.FixedURLEntry):
    id = 'emails-sync'
    label = _('Synchronization of incoming emails')
    permissions = 'emails'
    url_name = 'emails__sync_portal'
