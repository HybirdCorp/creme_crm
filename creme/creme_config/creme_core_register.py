# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import creme_menu, block_registry

from creme.creme_config.blocks import blocks_list


creme_registry.register_app('creme_config', _(u'General configuration') , '/creme_config')

reg_item = creme_menu.register_app('creme_config', '/creme_config/').register_item
reg_item('/creme_config/',                      _(u"Portal of general configuration"), 'creme_config.can_admin')
reg_item('/creme_config/relation_type/portal/', _(u"Relation types settings"),         'creme_config.can_admin')
reg_item('/creme_config/property_type/portal/', _(u"Property types settings"),         'creme_config.can_admin')
reg_item('/creme_config/custom_fields/portal/', _(u"Custom fields settings"),          'creme_config.can_admin')
reg_item('/creme_config/blocks/portal/',        _(u"Blocks settings"),                 'creme_config.can_admin')
reg_item('/creme_config/prefered_menu/edit/',   _(u"Default prefered menu settings"),  'creme_config.can_admin')
reg_item('/creme_config/button_menu/portal/',   _(u"Button menu settings"),            'creme_config.can_admin')
reg_item('/creme_config/search/portal/',        _(u"Search settings"),                 'creme_config.can_admin')
reg_item('/creme_config/history/portal/',       _(u"History settings"),                'creme_config.can_admin')
reg_item('/creme_config/user/portal/',          _(u'Users settings'),                  'creme_config.can_admin')
reg_item('/creme_config/role/portal/',          _(u'Roles and credentials settings'),  'creme_config.can_admin')

block_registry.register(*blocks_list)
