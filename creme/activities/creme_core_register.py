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
from creme_core.gui.button_menu import button_registry

from activities.models import Activity
from activities.blocks import participants_block, subjects_block, future_activities_block, past_activities_block, user_calendars_block
from activities.buttons import add_meeting_button, add_phonecall_button, add_task_button


creme_registry.register_app('activities', _(u'Activities'), '/activities')
creme_registry.register_entity_models(Activity)

reg_item = creme_menu.register_app('activities', '/activities/').register_item
reg_item('/activities/',                    _(u'Portal'),                 'activities')
reg_item('/activities/calendar/user',       _(u'Calendar'),               'activities')
reg_item('/activities/indisponibility/add', _(u'Add an indisponibility'), 'activities.add_activity')
reg_item('/activities/activities',          _(u'All activities'),         'activities')

block_registry.register(participants_block, subjects_block, future_activities_block, past_activities_block, user_calendars_block)

button_registry.register(add_meeting_button, add_phonecall_button, add_task_button)
