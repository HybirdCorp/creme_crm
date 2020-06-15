# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class EmailsConfig(CremeAppConfig):
    name = 'creme.emails'
    verbose_name = _('Emails')
    dependencies = ['creme.persons', 'creme.documents']

    def all_apps_ready(self):
        from . import (get_emailcampaign_model, get_entityemail_model,
                get_emailtemplate_model, get_mailinglist_model)

        self.EmailCampaign = get_emailcampaign_model()
        self.EmailTemplate = get_emailtemplate_model()
        self.EntityEmail   = get_entityemail_model()
        self.MailingList   = get_mailinglist_model()
        super().all_apps_ready()

        from . import signals  # NOQA

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.EmailCampaign,
                                              self.MailingList,
                                              self.EmailTemplate,
                                              self.EntityEmail,
                                             )

    def register_actions(self, actions_registry):
        from . import actions

        actions_registry.register_instance_actions(
            actions.EntityEmailResendAction,
        ).register_bulk_actions(
            actions.BulkEntityEmailResendAction,
        )

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.EmailHTMLBodyBrick,
            bricks.SendingHTMLBodyBrick,
            bricks.TemplateHTMLBodyBrick,
            bricks.MailingListsBrick,
            bricks.EmailRecipientsBrick,
            bricks.ContactsBrick,
            bricks.OrganisationsBrick,
            bricks.ChildListsBrick,
            bricks.ParentListsBrick,
            bricks.AttachmentsBrick,
            bricks.SendingsBrick,
            bricks.SendingBrick,
            bricks.MailsBrick,
            bricks.MailsHistoryBrick,
            bricks.MailPopupBrick,
            bricks.LwMailPopupBrick,
            bricks.LwMailsHistoryBrick,
            bricks.MySignaturesBrick,
        ).register_hat(
            self.EntityEmail,
            main_brick_cls=bricks.EntityEmailBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from . import models

        register = bulk_update_registry.register
        register(self.MailingList, exclude=('children', 'contacts', 'organisations'))
        register(self.EmailCampaign, exclude=('mailing_lists',))
        register(models.EmailSending, exclude=('sender', 'type', 'sending_date'))  # TODO: tags modifiable=False ??
        register(self.EntityEmail, exclude=('sender', 'recipient', 'subject',
                                            'body', 'body_html', 'signature', 'attachments',
                                           )  # TODO: idem
                )
        register(models.LightWeightEmail, exclude=('sender', 'recipient', 'subject', 'body'))  # TODO: idem

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.EntityEmailLinkButton)

    def register_fields_config(self, fields_config_registry):
        from creme import persons

        fields_config_registry.register_needed_fields('emails',
                                                      persons.get_contact_model(),
                                                      'email',
                                                     ) \
                              .register_needed_fields('emails',
                                                      persons.get_organisation_model(),
                                                      'email',
                                                     )

    def register_creme_config(self, config_registry):
        from . import bricks

        config_registry.register_user_bricks(bricks.MySignaturesBrick)

    def register_icons(self, icon_registry):
        from . import models

        icon_registry.register(self.EntityEmail,        'images/email_%(size)s.png') \
                     .register(models.LightWeightEmail, 'images/email_%(size)s.png') \
                     .register(models.EmailSending,     'images/email_%(size)s.png') \
                     .register(self.MailingList,        'images/email_%(size)s.png') \
                     .register(self.EmailCampaign,      'images/email_%(size)s.png') \
                     .register(self.EmailTemplate,      'images/email_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.apps import apps
        from django.urls import reverse_lazy as reverse

        ECampaign = self.EmailCampaign
        MList     = self.MailingList
        ETemplate = self.EmailTemplate

        group = creme_menu.get('features') \
                          .get_or_create(creme_menu.ContainerItem, 'marketing', priority=200,
                                         defaults={'label': _('Marketing')},
                                        ) \
                          .get_or_create(creme_menu.ItemGroup, 'emails', priority=10)
        LvURLItem = creme_menu.URLItem.list_view

        group.add(LvURLItem('emails-campaigns', model=ECampaign),        priority=10) \
             .add(LvURLItem('emails-mlists',    model=MList),            priority=15) \
             .add(LvURLItem('emails-templates', model=ETemplate),        priority=20) \
             .add(LvURLItem('emails-emails',    model=self.EntityEmail), priority=25)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('marketing', _('Marketing'), priority=200) \
                  .add_link('emails-create_campaign', ECampaign, priority=10) \
                  .add_link('emails-create_mlist',    MList, priority=15) \
                  .add_link('emails-create_template', ETemplate, priority=20)

        if apps.is_installed('creme.crudity'):
            group.add(creme_menu.URLItem('emails-sync', url=reverse('emails__crudity_sync'),
                                         label=_('Synchronization of incoming emails'),
                                         perm='emails',
                                        ),
                      priority=100,
                     )

    def register_setting_keys(self, setting_key_registry):
        from . import setting_keys

        setting_key_registry.register(setting_keys.emailcampaign_sender)
