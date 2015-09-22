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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class EmailsConfig(CremeAppConfig):
    name = 'creme.emails'
    verbose_name = _(u'Emails')
    dependencies = ['creme.persons', 'creme.documents', 'creme.crudity']

    def ready(self):
        from . import (get_emailcampaign_model, get_entityemail_model,
                get_emailtemplate_model, get_mailinglist_model)

        self.EmailCampaign = get_emailcampaign_model()
        self.EmailTemplate = get_emailtemplate_model()
        self.EntityEmail   = get_entityemail_model()
        self.MailingList   = get_mailinglist_model()
        super(EmailsConfig, self).ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('emails', _(u'Emails'), '/emails')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.EmailCampaign,
                                              self.MailingList,
                                              self.EmailTemplate,
                                              self.EntityEmail,
                                             )

    def register_blocks(self, block_registry):
        from .blocks import blocks_list, EntityEmailBlock

        block_registry.register_4_model(self.EntityEmail, EntityEmailBlock())
        block_registry.register(*blocks_list)

    def register_bulk_update(self, bulk_update_registry):
        from .models import EmailSending

        register = bulk_update_registry.register
        register(self.MailingList,   exclude=('children', 'contacts', 'organisations',))
        register(self.EmailCampaign, exclude=('mailing_lists',))
        register(EmailSending,       exclude=('sender', 'type', 'sending_date')) # TODO: tags modifiable=False ??

    def register_buttons(self, button_registry):
        from .buttons import entityemail_link_button

        button_registry.register(entityemail_link_button)

    def register_fields_config(self, fields_config_registry):
        from creme.persons import get_contact_model, get_organisation_model

        reg_fields = fields_config_registry.register_needed_fields
        reg_fields('emails', get_contact_model(),      'email')
        reg_fields('emails', get_organisation_model(), 'email')

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.EntityEmail,   'images/email_%(size)s.png')
        reg_icon(self.MailingList,   'images/email_%(size)s.png')
        reg_icon(self.EmailCampaign, 'images/email_%(size)s.png')
        reg_icon(self.EmailTemplate, 'images/email_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        ECampaign = self.EmailCampaign
        MList     = self.MailingList
        ETemplate = self.EmailTemplate
        reg_item = creme_menu.register_app ('emails', '/emails/').register_item
        reg_item('/emails/',                         _(u'Portal of emails'),    'emails')
        reg_item(reverse('emails__list_campaigns'),  _(u'All campaigns'),       'emails')
        reg_item(reverse('emails__create_campaign'), ECampaign.creation_label,  cperm(ECampaign))
        reg_item(reverse('emails__list_mlists'),     _(u'All mailing lists'),   'emails')
        reg_item(reverse('emails__create_mlist'),    MList.creation_label,      cperm(MList))
        reg_item(reverse('emails__list_templates'),  _(u'All email templates'), 'emails')
        reg_item(reverse('emails__create_template'), ETemplate.creation_label,  cperm(ETemplate))
        reg_item(reverse('emails__list_emails'),     _(u'All emails'),          'emails')
        reg_item('/emails/synchronization',          _(u'Synchronization of incoming emails'), 'emails')

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import emailcampaign_sender

        setting_key_registry.register(emailcampaign_sender)
