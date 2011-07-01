# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.registry import creme_registry
from creme_core.gui import creme_menu, block_registry, button_registry, icon_registry

from commercial.models import Act, ActObjectivePattern, Strategy
from commercial.blocks import blocks_list
from commercial.buttons import complete_goal_button


creme_registry.register_app('commercial', _(u'Commercial strategy'), '/commercial')
creme_registry.register_entity_models(Act, ActObjectivePattern, Strategy)

reg_item = creme_menu.register_app('commercial', '/commercial/').register_item
reg_item('/commercial/',                      _(u'Portal of commercial strategy'), 'commercial')
reg_item('/commercial/market_segments',       _(u'All market segments'),           'commercial')
reg_item('/commercial/acts',                  _(u'All commercial actions'),        'commercial')
reg_item('/commercial/act/add',               _(u'Add a commercial action'),       'commercial.add_act')
reg_item('/commercial/strategies',            _(u'All strategies'),                'commercial')
reg_item('/commercial/strategy/add',          _(u'Add a strategy'),                'commercial.add_strategy')
reg_item('/commercial/objective_patterns',    _(u'All objective patterns'),        'commercial')
reg_item('/commercial/objective_pattern/add', _(u'Add an objective pattern'),      'commercial.add_actobjectivepattern')

reg_item = creme_menu.get_app_item('persons').register_item
reg_item('/commercial/salesmen',     _(u'All salesmen'),   'persons')
reg_item('/commercial/salesman/add', _(u'Add a salesman'), 'persons.add_contact')

block_registry.register(*blocks_list)

button_registry.register(complete_goal_button)

reg_icon = icon_registry.register
reg_icon(Act,                 'images/commercial_%(size)s.png')
reg_icon(ActObjectivePattern, 'images/commercial_%(size)s.png')
reg_icon(Strategy,            'images/commercial_%(size)s.png')
