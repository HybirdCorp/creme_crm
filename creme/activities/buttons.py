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

from creme_core.gui.button_menu import Button


_PERMISSION = 'activities.add_activity'

class AddMeetingButton(Button):
    id_           = Button.generate_id('activities', 'add_meeting')
    verbose_name  = _(u'Add a meeting')
    template_name = 'activities/templatetags/button_add_meeting.html'
    permission    = _PERMISSION


class AddPhoneCallButton(Button):
    id_           = Button.generate_id('activities', 'add_phonecall')
    verbose_name  = _(u'Add a phone call')
    template_name = 'activities/templatetags/button_add_phonecall.html'
    permission    = _PERMISSION


class AddTaskButton(Button):
    id_           = Button.generate_id('activities', 'add_task')
    verbose_name  = _(u'Add a task')
    template_name = 'activities/templatetags/button_add_task.html'
    permission    = _PERMISSION


add_meeting_button   = AddMeetingButton()
add_phonecall_button = AddPhoneCallButton()
add_task_button      = AddTaskButton()
