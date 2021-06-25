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


class PollsConfig(CremeAppConfig):
    default = True
    name = 'creme.polls'
    verbose_name = _('Polls')
    dependencies = ['creme.persons', 'creme.commercial']

    def all_apps_ready(self):
        from . import (
            get_pollcampaign_model,
            get_pollform_model,
            get_pollreply_model,
        )

        self.PollCampaign = get_pollcampaign_model()
        self.PollForm     = get_pollform_model()
        self.PollReply    = get_pollreply_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(
            self.PollForm,
            self.PollReply,
            self.PollCampaign,
        )

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.PollFormLinesBrick,
            bricks.PollReplyLinesBrick,
            bricks.PollRepliesBrick,
            bricks.PersonPollRepliesBrick,
            bricks.PollCampaignRepliesBrick,
        ).register_hat(
            self.PollForm,
            main_brick_cls=bricks.PollFormBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .forms.poll_reply import InnerEditPersonForm
        from .models import PollFormLine

        bulk_update_registry.register(
            self.PollReply, innerforms={'person': InnerEditPersonForm},
        )
        bulk_update_registry.register(PollFormLine, exclude=['type'])

    def register_creme_config(self, config_registry):
        from . import models

        config_registry.register_model(models.PollType, 'poll_type')

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.CAMPAIGN_CREATION_CFORM,
            custom_forms.CAMPAIGN_EDITION_CFORM,

            custom_forms.PFORM_CREATION_CFORM,
            custom_forms.PFORM_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.PollForm,
            self.PollReply,
            self.PollCampaign,
        )

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.PollForm,     'images/poll_%(size)s.png',
        ).register(
            self.PollReply,    'images/poll_%(size)s.png',
        ).register(
            self.PollCampaign, 'images/poll_%(size)s.png',
        )

    # def register_menu(self, creme_menu):
    #     PCampaign = self.PollCampaign
    #     PForm     = self.PollForm
    #     PReply    = self.PollReply
    #     LvURLItem = creme_menu.URLItem.list_view
    #     creme_menu.get(
    #         'features', 'tools',
    #     ).get_or_create(
    #         creme_menu.ItemGroup, 'polls',
    #         priority=300,
    #         defaults={'label': _('Polls')},
    #     ).add(
    #         LvURLItem('polls-pforms', model=PForm),
    #         priority=10,
    #     ).add(
    #         LvURLItem('polls-preplies', model=PReply),
    #         priority=20,
    #     ).add(
    #         LvURLItem('polls-campaigns', model=PCampaign),
    #         priority=30,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms',
    #     ).get_or_create_group(
    #         'tools', _('Tools'),
    #         priority=100,
    #     ).add_link(
    #         'polls-create_pform', PForm,
    #         priority=300,
    #     ).add_link(
    #         'polls-create_preply', PReply,
    #         priority=302,
    #     ).add_link(
    #         'polls-create_campaign', PCampaign,
    #         priority=304,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.PollFormsEntry,
            menu.PollRepliesEntry,
            menu.PollCampaignsEntry,

            menu.PollFormCreationEntry,
            menu.PollReplyCreationEntry,
            menu.PollCampaignCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            group_id='tools', label=_('Tools'), priority=100,
        ).add_link(
            'polls-create_pform',    self.PollForm,     priority=300,
        ).add_link(
            'polls-create_preply',   self.PollReply,    priority=302,
        ).add_link(
            'polls-create_campaign', self.PollCampaign, priority=304,
        )
