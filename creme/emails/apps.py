################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
    default = True
    name = 'creme.emails'
    verbose_name = _('Emails')
    dependencies = ['creme.persons', 'creme.documents']

    def all_apps_ready(self):
        from creme import emails

        self.EmailCampaign = emails.get_emailcampaign_model()
        self.EmailTemplate = emails.get_emailtemplate_model()
        self.EntityEmail   = emails.get_entityemail_model()
        self.MailingList   = emails.get_mailinglist_model()
        super().all_apps_ready()

        from . import signals  # NOQA

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(
            self.EmailCampaign,
            self.MailingList,
            self.EmailTemplate,
            self.EntityEmail,
        )

    # def register_actions(self, actions_registry):
    def register_actions(self, action_registry):
        from . import actions

        action_registry.register_instance_actions(
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
            bricks.EmailsToSyncBrick,
        ).register_hat(
            self.EntityEmail,
            main_brick_cls=bricks.EntityEmailBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        # from . import models

        register = bulk_update_registry.register
        register(self.EmailCampaign).exclude('mailing_lists')
        register(self.MailingList).exclude('mailing_lists')
        # TODO: inner-form for body_html when RichTextEditor is ok in inner-popup
        register(self.EmailTemplate).exclude('body_html')
        # TODO: idem
        register(self.EntityEmail).exclude(
            'sender', 'recipient',
            'subject', 'body', 'body_html',
            'signature', 'attachments',
        )
        # TODO: idem
        # register(
        #     models.LightWeightEmail,
        #     exclude=('sender', 'recipient', 'subject', 'body'),
        # )

    def register_buttons(self, button_registry):
        from . import buttons

        button_registry.register(buttons.EntityEmailLinkButton)

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.CAMPAIGN_CREATION_CFORM,
            custom_forms.CAMPAIGN_EDITION_CFORM,

            custom_forms.TEMPLATE_CREATION_CFORM,
            custom_forms.TEMPLATE_EDITION_CFORM,

            custom_forms.MAILINGLIST_CREATION_CFORM,
            custom_forms.MAILINGLIST_EDITION_CFORM,
        )

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.MailingList, cloner_class=cloners.MailingListCloner,
        ).register(
            model=self.EmailTemplate,
        ).register(
            model=self.EmailCampaign,
        )
        # Not self.EntityEmail

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(
            model=self.EntityEmail,
        ).register(
            model=self.MailingList,
        ).register(
            model=self.EmailTemplate,
        ).register(
            model=self.EmailCampaign,
        )

    def register_fields_config(self, fields_config_registry):
        from creme import persons

        fields_config_registry.register_models(
            self.EmailCampaign,
            self.MailingList,
            self.EmailTemplate,
            self.EntityEmail,
        ).register_needed_fields(
            'emails', persons.get_contact_model(), 'email',
        ).register_needed_fields(
            'emails', persons.get_organisation_model(), 'email',
        )

    def register_creme_config(self, config_registry):
        from . import bricks

        config_registry.register_user_bricks(bricks.MySignaturesBrick)
        config_registry.register_app_bricks(
            'emails',
            bricks.SendingConfigItemsBrick,
            bricks.EmailSyncConfigItemsBrick,
        )

    def register_icons(self, icon_registry):
        from . import models

        icon_registry.register(
            self.EntityEmail,        'images/email_%(size)s.png',
        ).register(
            models.LightWeightEmail, 'images/email_%(size)s.png',
        ).register(
            models.EmailSending,     'images/email_%(size)s.png',
        ).register(
            self.MailingList,        'images/email_%(size)s.png',
        ).register(
            self.EmailCampaign,      'images/email_%(size)s.png',
        ).register(
            self.EmailTemplate,      'images/email_%(size)s.png',
        )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.EmailCampaignsEntry,
            menu.MailingListsEntry,
            menu.EmailTemplatesEntry,
            menu.EntityEmailsEntry,

            menu.EmailCampaignCreationEntry,
            menu.MailingListCreationEntry,
            menu.EmailTemplateCreationEntry,

            menu.EmailSyncEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'marketing', _('Marketing'), priority=200,
        ).add_link(
            'emails-create_campaign', self.EmailCampaign, priority=10,
        ).add_link(
            'emails-create_mlist',    self.MailingList,   priority=15,
        ).add_link(
            'emails-create_template', self.EmailTemplate, priority=20,
        )

    def register_notification(self, notification_registry):
        from . import notification

        notification_registry.register_content(
            content_cls=notification.CampaignSentContent,
        )

    def register_workflows(self, workflow_registry):
        from . import workflows

        workflow_registry.register_actions(
            workflows.EmailSendingAction,
            workflows.TemplateSendingAction,
        )
