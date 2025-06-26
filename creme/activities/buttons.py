################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.icons import get_icon_by_name, get_icon_size_px

from . import constants, get_activity_model

Activity = get_activity_model()


class AddRelatedActivityButton(Button):
    id = Button.generate_id('activities', 'add_activity')
    template_name = 'activities/buttons/add-related.html'
    permissions = build_creation_perm(Activity)
    verbose_name = _('Create a related activity')
    description = _(
        'This button displays the creation form for activities (meetings, phone calls…). '
        'The current entity is pre-selected to be linked to the created activity.\n'
        'App: Activities'
    )
    activity_type_uuid: str | None = None  # None means type is not fixed

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)
        request.user.has_perm_to_link_or_die(entity)

    def get_context(self, *, entity, request):
        context = super().get_context(entity=entity, request=request)
        type_uuid = self.activity_type_uuid
        context['type_uuid'] = type_uuid

        icon_info = constants.ICONS.get(type_uuid)
        if icon_info:
            name, label = icon_info
        else:
            name = 'calendar'
            label = Activity._meta.verbose_name

        theme = request.user.theme_info[0]
        context['icon'] = get_icon_by_name(
            name=name, label=label, theme=theme,
            size_px=get_icon_size_px(theme=theme, size='instance-button'),
        )

        return context


class AddMeetingButton(AddRelatedActivityButton):
    id = Button.generate_id('activities', 'add_meeting')
    verbose_name = _('Create a related meeting')
    description = _(
        'This button displays the creation form for meetings (kind of activity). '
        'The current entity is pre-selected to be linked to the created meeting.\n'
        'App: Activities'
    )
    activity_type_uuid = constants.UUID_TYPE_MEETING


class AddPhoneCallButton(AddRelatedActivityButton):
    id = Button.generate_id('activities', 'add_phonecall')
    verbose_name = _('Create a related phone call')
    description = _(
        'This button displays the creation form for phone calls (kind of activity). '
        'The current entity is pre-selected to be linked to the created phone call.\n'
        'App: Activities'
    )
    activity_type_uuid = constants.UUID_TYPE_PHONECALL


class AddTaskButton(AddRelatedActivityButton):
    id = Button.generate_id('activities', 'add_task')
    verbose_name = _('Create a related task')
    description = _(
        'This button displays the creation form for tasks (kind of activity). '
        'The current entity is pre-selected to be linked to the created task.\n'
        'App: Activities'
    )
    activity_type = constants.UUID_TYPE_TASK


class AddUnsuccessfulPhoneCallButton(AddRelatedActivityButton):
    id = Button.generate_id('activities', 'add_unsuccessful_phonecall')
    verbose_name = _('Create an unsuccessful phone call')
    template_name = 'activities/buttons/add-unsuccessful-phonecall.html'
    permissions = build_creation_perm(Activity)
    description = _(
        'This button creates a short phone call (kind of activity) which was '
        'not successful (in order to keep a history).\n'
        'The current contact participates in the created call, & you too.\n'
        'The fields values can be set in the configuration of «Activities».\n'
        'App: Activities'
    )

    def check_permissions(self, *, entity, request):
        super().check_permissions(entity=entity, request=request)

        user = request.user
        user.has_perm_to_link_or_die(entity)

        if entity == user.linked_contact:
            raise ConflictError(_('You cannot call yourself'))

    def get_ctypes(self):
        from creme.persons import get_contact_model

        return [get_contact_model()]
