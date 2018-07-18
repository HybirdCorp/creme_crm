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


class EventsConfig(CremeAppConfig):
    name = 'creme.events'
    verbose_name = _(u'Events')
    dependencies = ['creme.persons', 'creme.opportunities']

    def all_apps_ready(self):
        from . import get_event_model

        self.Event = get_event_model()
        # super(EventsConfig, self).all_apps_ready()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Event)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ResutsBrick)
        brick_registry.register_hat(self.Event, main_brick_cls=bricks.EventBarHatBrick)

    def register_icons(self, icon_registry):
        icon_registry.register(self.Event, 'images/event_%(size)s.png')

    def register_menu(self, creme_menu):
        # from django.conf import settings

        Event = self.Event

        # if settings.OLD_MENU:
        #     from django.urls import reverse_lazy as reverse
        #     from creme.creme_core.auth import build_creation_perm
        #
        #     reg_item = creme_menu.register_app('events', '/events/').register_item
        #     reg_item(reverse('events__portal'),       _(u'Portal of events'), 'events')
        #     reg_item(reverse('events__list_events'),  _(u'All events'),       'events')
        #     reg_item(reverse('events__create_event'), Event.creation_label,   build_creation_perm(Event))
        # else:
        creme_menu.get('features', 'tools') \
                  .add(creme_menu.URLItem.list_view('events-events', model=Event), priority=200)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('tools', _(u'Tools'), priority=100) \
                  .add_link('events-create_event', Event, priority=200)
