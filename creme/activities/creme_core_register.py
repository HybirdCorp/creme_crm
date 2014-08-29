# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from creme.creme_core.gui import (creme_menu, block_registry, button_registry,
        icon_registry, bulk_update_registry, import_form_registry, smart_columns_registry)
from creme.creme_core.registry import creme_registry

from .blocks import block_list
from .buttons import add_activity_button, add_meeting_button, add_phonecall_button, add_task_button
from .constants import REL_OBJ_PART_2_ACTIVITY, REL_OBJ_ACTIVITY_SUBJECT
from .forms.lv_import import get_csv_form_builder
from .models import Activity


creme_registry.register_app('activities', _(u'Activities'), '/activities')
creme_registry.register_entity_models(Activity)

reg_item = creme_menu.register_app('activities', '/activities/').register_item
reg_item('/activities/',                       _(u"Portal of activities"),   'activities')
reg_item('/activities/calendar/user',          _(u'Calendar'),               'activities')
reg_item('/activities/activity/add',           Activity.creation_label,      'activities.add_activity')
reg_item('/activities/activity/add/meeting',   _(u'Add a meeting'),          'activities.add_activity')
reg_item('/activities/activity/add/phonecall', _(u'Add a phone call'),       'activities.add_activity')
reg_item('/activities/activity/add/task',      _(u'Add a task'),             'activities.add_activity')
reg_item('/activities/activity/add_indispo',   _(u'Add an indisponibility'), 'activities.add_activity')
reg_item('/activities/activities',             _(u'All activities'),         'activities')
reg_item('/activities/phone_calls',            _(u'All phone calls'),        'activities')
reg_item('/activities/meetings',               _(u'All meetings'),           'activities')

block_registry.register(*block_list)

button_registry.register(add_activity_button, add_meeting_button, add_phonecall_button, add_task_button)

icon_registry.register(Activity, 'images/calendar_%(size)s.png')

bulk_update_registry.register(
    #(Activity,  ['type', 'start', 'end', 'busy', 'is_all_day', 'sub_type']),
    (Activity,  ['start', 'end', 'busy', 'is_all_day', 'sub_type']),
)

import_form_registry.register(Activity, get_csv_form_builder)

smart_columns_registry.register_model(Activity).register_field('title') \
                                               .register_field('start') \
                                               .register_relationtype(REL_OBJ_PART_2_ACTIVITY) \
                                               .register_relationtype(REL_OBJ_ACTIVITY_SUBJECT)
