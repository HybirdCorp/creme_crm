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
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry

from creme_config.blocks import blocks_list


creme_registry.register_app('creme_config', _(u'General configuration') , '/creme_config')

creme_menu.register_app('creme_config', '/creme_config/', 'Configuration générale')
reg_menu = creme_menu.register_menu
reg_menu('creme_config', '/creme_config/',                      _(u"Portal"))
reg_menu('creme_config', '/creme_config/relation_type/portal/', _(u"Relation types settings"))
reg_menu('creme_config', '/creme_config/property_type/portal/', _(u"Property types settings"))
reg_menu('creme_config', '/creme_config/custom_fields/portal/', _(u"Custom fields settings"))
reg_menu('creme_config', '/creme_config/blocks/portal/',        _(u"Blocks settings"))
reg_menu('creme_config', '/creme_config/prefered_menu/edit/',   _(u"Default prefered menu settings"))
reg_menu('creme_config', '/creme_config/button_menu/portal/',   _(u"Button menu settings"))
reg_menu('creme_config', '/creme_config/search/portal/',        _(u"Search settings"))
reg_menu('creme_config', '/creme_config/user/portal/',          _(u'Users settings'))
reg_menu('creme_config', '/creme_config/role/portal/',          _(u'Roles and credentials settings'))

block_registry.register(*blocks_list)
