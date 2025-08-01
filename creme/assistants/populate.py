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

from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.core import notification
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    NotificationChannel,
    SettingValue,
)

from . import constants
from .bricks import AlertsBrick, MemosBrick, TodosBrick, UserMessagesBrick
from .models import UserMessagePriority
from .notification import UserMessagesChannelType
from .setting_keys import todo_reminder_key


class Populator(BasePopulator):
    dependencies = ['creme_core']

    SETTING_VALUES = [
        SettingValue(key=todo_reminder_key, value=9),
    ]
    NOTIFICATION_CHANNELS = [
        NotificationChannel(
            uuid=constants.UUID_CHANNEL_USERMESSAGES,
            type=UserMessagesChannelType,
            required=True,
            default_outputs=[notification.OUTPUT_EMAIL, notification.OUTPUT_WEB],
        ),
    ]
    PRIORITIES = [
        UserMessagePriority(
            uuid=constants.UUID_PRIORITY_IMPORTANT,
            title=_('Important'),
            is_custom=False,
        ),
        UserMessagePriority(
            uuid=constants.UUID_PRIORITY_VERY_IMPORTANT,
            title=_('Very important'),
            is_custom=False,
        ),
        UserMessagePriority(
            uuid=constants.UUID_PRIORITY_NOT_IMPORTANT,
            title=_('Not important'),
            is_custom=False,
        ),
    ]

    def _already_populated(self):
        return UserMessagePriority.objects.exists()

    def _populate(self):
        self._populate_message_priorities()
        super()._populate()

    def _populate_message_priorities(self):
        self._save_minions(self.PRIORITIES)

    def _populate_bricks_config(self):
        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT,
        )
        create_bdl(brick=TodosBrick,        order=100)
        create_bdl(brick=MemosBrick,        order=200)
        create_bdl(brick=AlertsBrick,       order=300)
        create_bdl(brick=UserMessagesBrick, order=400)

        create_bhl = BrickHomeLocation.objects.create
        create_bhl(brick_id=MemosBrick.id,        order=100)
        create_bhl(brick_id=AlertsBrick.id,       order=200)
        create_bhl(brick_id=UserMessagesBrick.id, order=300)
