# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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


class SMSConfig(CremeAppConfig):
    default = True
    name = 'creme.sms'
    verbose_name = _('SMS')
    dependencies = ['creme.persons']

    def all_apps_ready(self):
        from . import (
            get_messagetemplate_model,
            get_messaginglist_model,
            get_smscampaign_model,
        )

        self.SMSCampaign     = get_smscampaign_model()
        self.MessagingList   = get_messaginglist_model()
        self.MessageTemplate = get_messagetemplate_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(
            self.SMSCampaign,
            self.MessagingList,
            self.MessageTemplate,
        )

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.MessagingListsBlock,
            bricks.RecipientsBrick,
            bricks.ContactsBrick,
            bricks.MessagesBrick,
            bricks.SendingsBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        bulk_update_registry.register(self.SMSCampaign, exclude=('lists',))

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.CAMPAIGN_CREATION_CFORM,
            custom_forms.CAMPAIGN_EDITION_CFORM,

            custom_forms.TEMPLATE_CREATION_CFORM,
            custom_forms.TEMPLATE_EDITION_CFORM,

            custom_forms.MESSAGINGLIST_CREATION_CFORM,
            custom_forms.MESSAGINGLIST_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        from creme import persons

        # TODO ?
        # fields_config_registry.register_models(
        #     self.SMSCampaign,
        #     self.MessagingList,
        #     self.MessageTemplate,
        # )
        fields_config_registry.register_needed_fields(
            'sms',
            persons.get_contact_model(),
            'mobile',
        )

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.SMSCampaign,     'images/sms_%(size)s.png',
        ).register(
            self.MessagingList,   'images/sms_%(size)s.png',
        ).register(
            self.MessageTemplate, 'images/sms_%(size)s.png',
        )

    # def register_menu(self, creme_menu):
    #     SMSCampaign = self.SMSCampaign
    #     MList       = self.MessagingList
    #     MTemplate   = self.MessageTemplate
    #     LvURLItem = creme_menu.URLItem.list_view
    #
    #     creme_menu.get(
    #         'features'
    #     ).get_or_create(
    #         creme_menu.ContainerItem, 'marketing',
    #         priority=200,
    #         defaults={'label': _('Marketing')},
    #     ).get_or_create(
    #         creme_menu.ItemGroup, 'sms', priority=20,
    #     ).add(
    #         LvURLItem('sms-campaigns', model=SMSCampaign), priority=200,
    #     ).add(
    #         LvURLItem('sms-mlists',    model=MList),       priority=210,
    #     ).add(
    #         LvURLItem('sms-templates', model=MTemplate),   priority=220,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms'
    #     ).get_or_create_group(
    #         'marketing', _('Marketing'), priority=200,
    #     ).add_link(
    #         'sms-create_campaign', SMSCampaign, priority=200,
    #     ).add_link(
    #         'sms-create_mlist',    MList,       priority=210,
    #     ).add_link(
    #         'sms-create_template', MTemplate,   priority=220,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.SMSCampaignsEntry,
            menu.MessagingListsEntry,
            menu.MessageTemplatesEntry,

            menu.SMSCampaignCreationEntry,
            menu.MessagingListCreationEntry,
            menu.MessageTemplateCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            group_id='marketing', label=_('Marketing'), priority=200,
        ).add_link(
            'sms-create_campaign', self.SMSCampaign,     priority=200,
        ).add_link(
            'sms-create_mlist',    self.MessagingList,   priority=210,
        ).add_link(
            'sms-create_template', self.MessageTemplate, priority=220,
        )
