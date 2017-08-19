# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.icons import get_icon_by_name, get_icon_size_px
from creme.creme_core.utils.media import get_current_theme_from_context

from . import get_activity_model, constants


Activity = get_activity_model()


class AddRelatedActivityButton(Button):
    id_           = Button.generate_id('activities', 'add_activity')
    template_name = 'activities/templatetags/button_add_related.html'
    permission    = cperm(Activity)
    verbose_name  = _(u'Create a related activity')
    activity_type = None  # None means type is not fixed

    def render(self, context):
        context['activity_type'] = self.activity_type
        context['verbose_name'] = self.verbose_name

        icon_info = constants.ICONS.get(self.activity_type)
        if icon_info:
            name, label = icon_info
        else:
            name = 'calendar'
            label = Activity._meta.verbose_name

        theme = get_current_theme_from_context(context)
        context['icon'] = get_icon_by_name(name=name, label=label, theme=theme,
                                           size_px=get_icon_size_px(theme=theme, size='instance-button'),
                                          )

        return super(AddRelatedActivityButton, self).render(context)


class AddMeetingButton(AddRelatedActivityButton):
    id_           = Button.generate_id('activities', 'add_meeting')
    verbose_name  = _(u'Create a related meeting')
    activity_type = constants.ACTIVITYTYPE_MEETING


class AddPhoneCallButton(AddRelatedActivityButton):
    id_           = Button.generate_id('activities', 'add_phonecall')
    verbose_name  = _(u'Create a related phone call')
    activity_type = constants.ACTIVITYTYPE_PHONECALL


class AddTaskButton(AddRelatedActivityButton):
    id_           = Button.generate_id('activities', 'add_task')
    verbose_name  = _(u'Create a related task')
    activity_type = constants.ACTIVITYTYPE_TASK


add_activity_button  = AddRelatedActivityButton()
add_meeting_button   = AddMeetingButton()
add_phonecall_button = AddPhoneCallButton()
add_task_button      = AddTaskButton()
