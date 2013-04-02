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

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui.menu import creme_menu


creme_registry.register_app("crudity", _(u'External data management'), '/crudity')

reg_item = creme_menu.register_app("crudity", '/crudity/').register_item
#reg_item('/crudity/',                       _(u'Portal'))
reg_item('/crudity/waiting_actions',  _(u'Email waiting actions'), 'crudity')
reg_item('/crudity/history',                _(u'History'),               'crudity')


