################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2024  Hybird
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
        from .forms.poll_reply import PersonOverrider

        register = bulk_update_registry.register
        register(self.PollForm)
        register(self.PollReply).add_overriders(PersonOverrider)
        register(self.PollCampaign)
        # bulk_update_registry.register(PollFormLine).exclude('type') TODO ??

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

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.PollForm, cloner_class=cloners.PollFormCloner,
        )
        # TODO?
        #  .register(model=self.PollReply).register( model=self.PollCampaign)

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(
            model=self.PollForm,
        ).register(
            model=self.PollReply,
        ).register(
            model=self.PollCampaign,
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
