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

from commercial.models.act import Act
from commercial.blocks import approaches_block


creme_registry.register_app('commercial', _(u'Commercial strategy'), '/commercial')
creme_registry.register_entity_models(Act)

#TODO: i18n
creme_menu.register_app('commercial', '/commercial/', 'Commercial')
reg_menu = creme_menu.register_menu
reg_menu('commercial', '/commercial/',             _(u'Portal'))
reg_menu('commercial', '/commercial/acts',         _(u'All commercial actions'))
reg_menu('commercial', '/commercial/act/add',      _(u'Add a commercial action'))
reg_menu('persons',    '/commercial/salesmen',     _(u'All salesmen'))
reg_menu('persons',    '/commercial/salesman/add', _(u'Add a salesman'))

block_registry.register(approaches_block)
