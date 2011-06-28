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

from creme_core.registry import creme_registry
from creme_core.gui import creme_menu, icon_registry

from recurrents.models import RecurrentGenerator


creme_registry.register_app('recurrents', _(u'Recurrent documents'), '/recurrents')
creme_registry.register_entity_models(RecurrentGenerator)

reg_item = creme_menu.register_app('recurrents', '/recurrents/').register_item
reg_item('/recurrents/',              _(u'Portal'),                   'recurrents')
reg_item('/recurrents/generators',    _(u'All recurrent generators'), 'recurrents')
reg_item('/recurrents/generator/add', _(u'Add a generator'),          'recurrents.add_recurrentgenerator')

icon_registry.register(RecurrentGenerator, 'images/recurrent_doc_%(size)s.png')
