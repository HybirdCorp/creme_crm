# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.SMSCampaign,
                                              self.MessagingList,
                                              self.MessageTemplate,
                                             )

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.MessagingListsBlock,
                                bricks.RecipientsBrick,
                                bricks.ContactsBrick,
                                bricks.MessagesBrick,
                                bricks.SendingsBrick,
                               )

    def register_bulk_update(self, bulk_update_registry):
        bulk_update_registry.register(self.SMSCampaign, exclude=('lists',))

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.SMSCampaign,     'images/sms_%(size)s.png')
        reg_icon(self.MessagingList,   'images/sms_%(size)s.png')
        reg_icon(self.MessageTemplate, 'images/sms_%(size)s.png')

    def register_menu(self, creme_menu):
        # from django.conf import settings
        # from django.urls import reverse_lazy as reverse

        SMSCampaign = self.SMSCampaign
        MList       = self.MessagingList
        MTemplate   = self.MessageTemplate

        # if settings.OLD_MENU:
        #     from creme.creme_core.auth import build_creation_perm
        #
        #     reg_item = creme_menu.register_app('sms', '/sms/').register_item
        #     reg_item(reverse('sms__portal'),          _(u'Portal of SMS'),         'sms')
        #     reg_item(reverse('sms__list_campaigns'),  _(u'All campaigns'),         'sms')
        #     reg_item(reverse('sms__create_campaign'), SMSCampaign.creation_label,  build_creation_perm(SMSCampaign))
        #     reg_item(reverse('sms__list_mlists'),     _(u'All messaging lists'),   'sms')
        #     reg_item(reverse('sms__create_mlist'),    MList.creation_label,        build_creation_perm(MList))
        #     reg_item(reverse('sms__list_templates'),  _(u'All message templates'), 'sms')
        #     reg_item(reverse('sms__create_template'), MTemplate.creation_label,    build_creation_perm(MTemplate))
        # else:
        LvURLItem = creme_menu.URLItem.list_view

        creme_menu.get('features') \
                  .get_or_create(creme_menu.ContainerItem, 'marketing', priority=200,
                                 defaults={'label': _(u'Marketing')},
                                ) \
                  .get_or_create(creme_menu.ItemGroup, 'sms', priority=20) \
                  .add(LvURLItem('sms-campaigns', model=SMSCampaign), priority=200) \
                  .add(LvURLItem('sms-mlists',    model=MList),       priority=210) \
                  .add(LvURLItem('sms-templates', model=MTemplate),   priority=220)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('marketing', _(u'Marketing'), priority=200) \
                  .add_link('sms-create_campaign', SMSCampaign, priority=200) \
                  .add_link('sms-create_mlist',    MList,       priority=210) \
                  .add_link('sms-create_template', MTemplate,   priority=220)
