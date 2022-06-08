################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from __future__ import annotations

from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.buttons import ActionButton
from creme.creme_core.gui.button_menu import Button

from . import constants, get_activity_model

Activity = get_activity_model()


class AddRelatedActivityButton(ActionButton):
    # id_ = Button.generate_id('activities', 'add_activity')
    id = Button.generate_id('activities', 'add_activity')
    permissions = build_creation_perm(Activity)
    verbose_name = _('Create a related activity')
    description = _(
        'This button displays the creation form for activities (meetings, phone calls…). '
        'The current entity is pre-selected to be linked to the created activity.\n'
        'App: Activities'
    )
    activity_type: str | None = None  # None means type is not fixed

    def eval_action_url(self, context):
        url = reverse('activities__create_related_activity', args=(context['object'].id,))
        url += f'?callback_url={context["request"].path}'

        if self.activity_type:
            url += f'&activity_type={self.activity_type}'

        return url

    def get_icon_info(self):
        return constants.ICONS.get(self.activity_type, ('calendar', Activity._meta.verbose_name))

    def get_template_context(self, context: dict) -> dict:
        icon, icon_title = self.get_icon_info()

        ctx = super().get_template_context(context)
        ctx['icon'] = icon
        ctx['icon_title'] = icon_title

        return ctx


class AddMeetingButton(AddRelatedActivityButton):
    # id_ = Button.generate_id('activities', 'add_meeting')
    id = Button.generate_id('activities', 'add_meeting')
    verbose_name = _('Create a related meeting')
    description = _(
        'This button displays the creation form for meetings (kind of activity). '
        'The current entity is pre-selected to be linked to the created meeting.\n'
        'App: Activities'
    )
    activity_type = constants.ACTIVITYTYPE_MEETING


class AddPhoneCallButton(AddRelatedActivityButton):
    # id_ = Button.generate_id('activities', 'add_phonecall')
    id = Button.generate_id('activities', 'add_phonecall')
    verbose_name = _('Create a related phone call')
    description = _(
        'This button displays the creation form for phone calls (kind of activity). '
        'The current entity is pre-selected to be linked to the created phone call.\n'
        'App: Activities'
    )
    activity_type = constants.ACTIVITYTYPE_PHONECALL


class AddTaskButton(AddRelatedActivityButton):
    # id_ = Button.generate_id('activities', 'add_task')
    id = Button.generate_id('activities', 'add_task')
    verbose_name = _('Create a related task')
    description = _(
        'This button displays the creation form for tasks (kind of activity). '
        'The current entity is pre-selected to be linked to the created task.\n'
        'App: Activities'
    )
    activity_type = constants.ACTIVITYTYPE_TASK
