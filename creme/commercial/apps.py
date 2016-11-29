# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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


class CommercialConfig(CremeAppConfig):
    name = 'creme.commercial'
    verbose_name = _(u'Commercial strategy')
    dependencies = ['creme.persons', 'creme.opportunities']

    def all_apps_ready(self):
        from . import get_act_model, get_pattern_model, get_strategy_model

        self.Act      = get_act_model()
        self.Pattern  = get_pattern_model()
        self.Strategy = get_strategy_model()
        super(CommercialConfig, self).all_apps_ready()

        from . import signals

    # def register_creme_app(self, creme_registry):
    #     creme_registry.register_app('commercial', _(u'Commercial strategy'), '/commercial')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Act, self.Pattern, self.Strategy)

    def register_blocks(self, block_registry):
        from .blocks import blocks_list

        block_registry.register(*blocks_list)

    def register_bulk_update(self, bulk_update_registry):
        from .models import ActObjectivePatternComponent, MarketSegmentDescription

        register = bulk_update_registry.register
        register(ActObjectivePatternComponent, exclude=['success_rate'])  # TODO: min_value/max_value constraint in the model... )
        register(MarketSegmentDescription,     exclude=['segment'])  # TODO: special form for segment

    def register_buttons(self, button_registry):
        from .buttons import complete_goal_button

        button_registry.register(complete_goal_button)

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Act,      'images/commercial_%(size)s.png')
        reg_icon(self.Pattern,  'images/commercial_%(size)s.png')
        reg_icon(self.Strategy, 'images/commercial_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        from creme.persons import get_contact_model

        Act      = self.Act
        Pattern  = self.Pattern
        Strategy = self.Strategy
        reg_item = creme_menu.register_app('commercial', '/commercial/').register_item
        reg_item('/commercial/',                         _(u'Portal of commercial strategy'), 'commercial')
        reg_item('/commercial/market_segments',          _(u'All market segments'),           'commercial')
        reg_item(reverse('commercial__list_acts'),       _(u'All commercial actions'),        'commercial')
        reg_item(reverse('commercial__create_act'),      Act.creation_label,                  cperm(Act))
        reg_item(reverse('commercial__list_strategies'), _(u'All strategies'),                'commercial')
        reg_item(reverse('commercial__create_strategy'), Strategy.creation_label,             cperm(Strategy))
        reg_item(reverse('commercial__list_patterns'),   _(u'All objective patterns'),        'commercial')
        reg_item(reverse('commercial__create_pattern'),  Pattern.creation_label,              cperm(Pattern))

        reg_item = creme_menu.get_app_item('persons').register_item
        reg_item(reverse('commercial__list_salesmen'),   _(u'All salesmen'),   'persons')
        reg_item(reverse('commercial__create_salesman'), _(u'Add a salesman'), cperm(get_contact_model()))

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import orga_approaches_key  # notification_key

        setting_key_registry.register(orga_approaches_key)  # notification_key
