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

from creme_core.gui.block import block_registry
from creme_core.gui.menu import creme_menu
from creme_core.registry import creme_registry

from activesync.blocks import user_mobile_sync_config_block, mobile_sync_config_block

block_registry.register(user_mobile_sync_config_block, mobile_sync_config_block)

creme_registry.register_app('activesync', _(u'Mobile synchronization') , None)

try:
    reg_item = creme_menu.get_app_item('persons').register_item
    reg_item('/activesync/sync', _(u'Contact synchronisation'), 'persons')
except KeyError:
    pass #persons app isn't installed

