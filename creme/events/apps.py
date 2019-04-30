# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2019  Hybird
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

        brick_registry.register(bricks.ResutsBrick)
        brick_registry.register_hat(self.Event, main_brick_cls=bricks.EventBarHatBrick)

    def register_creme_config(self, config_registry):
        from . import models

        config_registry.register_model(models.EventType, 'event_type')

    def register_icons(self, icon_registry):
        icon_registry.register(self.Event, 'images/event_%(size)s.png')

    def register_menu(self, creme_menu):
        Event = self.Event

        creme_menu.get('features', 'tools') \
                  .add(creme_menu.URLItem.list_view('events-events', model=Event), priority=200)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('tools', _('Tools'), priority=100) \
                  .add_link('events-create_event', Event, priority=200)
