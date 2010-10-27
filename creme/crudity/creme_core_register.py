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

from django.utils.translation import ugettext as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu


app_url  = '/crudity'
app_name = 'crudity'

creme_registry.register_app(app_name, _(u'External data management'), app_url)

creme_menu.register_app (app_name, '%s/' % app_url, "Gestion des données externes")
reg_menu = creme_menu.register_item
#reg_menu(app_name, '%s/' % app_url,                       _(u'Portal'))
reg_menu(app_name, '%s/email/waiting_actions' % app_url,  _(u'Email waiting actions'), 'crudity')
reg_menu(app_name, '%s/history' % app_url,                _(u'History'),               'crudity')

