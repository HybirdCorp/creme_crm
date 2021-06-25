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


class EventsConfig(CremeAppConfig):
    default = True
    name = 'creme.events'
    verbose_name = _('Events')
    dependencies = ['creme.persons', 'creme.opportunities']

    def all_apps_ready(self):
        from . import get_event_model

        self.Event = get_event_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Event)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ResultsBrick) \
                      .register_hat(self.Event, main_brick_cls=bricks.EventBarHatBrick)

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.EVENT_CREATION_CFORM,
            custom_forms.EVENT_EDITION_CFORM,
        )

    def register_creme_config(self, config_registry):
        from . import models

        config_registry.register_model(models.EventType, 'event_type')

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.Event)

    def register_icons(self, icon_registry):
        icon_registry.register(self.Event, 'images/event_%(size)s.png')

    # def register_menu(self, creme_menu):
    #     Event = self.Event
    #
    #     creme_menu.get('features', 'tools') \
    #               .add(creme_menu.URLItem.list_view('events-events', model=Event), priority=200)
    #     creme_menu.get('creation', 'any_forms') \
    #               .get_or_create_group('tools', _('Tools'), priority=100) \
    #               .add_link('events-create_event', Event, priority=200)

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.EventsEntry,
            menu.EventCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            group_id='tools', label=_('Tools'), priority=100,
        ).add_link('events-create_event', self.Event, priority=200)
