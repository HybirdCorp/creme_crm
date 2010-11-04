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

from events.models import Event


creme_registry.register_entity_models(Event)
creme_registry.register_app('events', _(u'Events'), '/events')

reg_item = creme_menu.register_app('events', '/events/').register_item
reg_item('/events/',          _(u'Portal'),       'events')
reg_item('/events/events',    _(u'All events'),   'events')
reg_item('/events/event/add', _(u'Add an event'), 'events.add_event')
