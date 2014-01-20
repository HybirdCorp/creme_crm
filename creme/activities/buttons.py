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

from creme.creme_core.gui.button_menu import Button

from .models import Activity
from .constants import ACTIVITYTYPE_MEETING, ACTIVITYTYPE_PHONECALL, ACTIVITYTYPE_TASK


class AddRelatedActivityButton(Button):
    id_           = Button.generate_id('activities', 'add_activity')
    template_name = 'activities/templatetags/button_add_related.html'
    permission    = 'activities.add_activity'
    verbose_name  = Activity.creation_label
    activity_type = None #None means type is not fixed

    def render(self, context):
        context['activity_type'] = atype = self.activity_type
        context['verbose_name'] = Activity.get_creation_title(atype)
        return super(AddRelatedActivityButton, self).render(context)


class AddMeetingButton(AddRelatedActivityButton):
    id_           = Button.generate_id('activities', 'add_meeting')
    verbose_name  = _(u'Add a meeting')
    activity_type = ACTIVITYTYPE_MEETING


class AddPhoneCallButton(AddRelatedActivityButton):
    id_           = Button.generate_id('activities', 'add_phonecall')
    verbose_name  = _(u'Add a phone call')
    activity_type = ACTIVITYTYPE_PHONECALL


class AddTaskButton(AddRelatedActivityButton):
    id_           = Button.generate_id('activities', 'add_task')
    verbose_name  = _(u'Add a task')
    activity_type = ACTIVITYTYPE_TASK


add_activity_button  = AddRelatedActivityButton()
add_meeting_button   = AddMeetingButton()
add_phonecall_button = AddPhoneCallButton()
add_task_button      = AddTaskButton()
