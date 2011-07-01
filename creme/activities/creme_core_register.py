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
from creme_core.gui import creme_menu, block_registry, button_registry, icon_registry, bulk_update_registry

from activities.models import Activity, PhoneCall, Meeting, Task
from activities.blocks import participants_block, subjects_block, future_activities_block, past_activities_block, user_calendars_block
from activities.buttons import add_meeting_button, add_phonecall_button, add_task_button
from activities.signals import connect_to_signals

connect_to_signals()

creme_registry.register_app('activities', _(u'Activities'), '/activities')
creme_registry.register_entity_models(Activity, PhoneCall, Meeting, Task)

reg_item = creme_menu.register_app('activities', '/activities/').register_item
reg_item('/activities/',                       _(u"Portal of activities"),   'activities')
reg_item('/activities/calendar/user',          _(u'Calendar'),               'activities')
reg_item('/activities/indisponibility/add',    _(u'Add an indisponibility'), 'activities.add_activity')
reg_item('/activities/activity/add/meeting',   _(u'Add a meeting'),          'activities.add_activity')
reg_item('/activities/activity/add/phonecall', _(u'Add a phone call'),       'activities.add_activity')
reg_item('/activities/activity/add/task',      _(u'Add a task'),             'activities.add_activity')
reg_item('/activities/activity/add/activity',  _(u'Add an activity'),        'activities.add_activity')
reg_item('/activities/activities',             _(u'All activities'),         'activities')

block_registry.register(participants_block, subjects_block, future_activities_block, past_activities_block, user_calendars_block)

button_registry.register(add_meeting_button, add_phonecall_button, add_task_button)

reg_icon = icon_registry.register
reg_icon(Activity,  'images/calendar_%(size)s.png')
reg_icon(PhoneCall, 'images/phone_%(size)s.png')
reg_icon(Meeting,   'images/map_%(size)s.png')
reg_icon(Task,      'images/task_%(size)s.png')

bulk_update_registry.register(
    (Activity, ['type', 'start_date', 'end_date', 'busy', 'is_all_day']),
)
