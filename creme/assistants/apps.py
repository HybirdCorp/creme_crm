################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2026  Hybird
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

from typing import override

from django.utils.translation import gettext_lazy as _

from creme.creme_config.apps import CremeConfigConfigMixin
from creme.creme_core.apps import CremeAppConfig


class AssistantsConfig(CremeConfigConfigMixin, CremeAppConfig):
    default = True
    name = 'creme.assistants'
    verbose_name = _('Assistants (Todos, Memos, …)')
    dependencies = ['creme.creme_core']

    def ready(self):
        super().ready()

        from . import signals  # NOQA

    @override
    def register_bricks(self, brick_registry):
        from . import bricks

        # brick_registry.register(
        #     bricks.TodosBrick,
        #     bricks.MemosBrick,
        #     bricks.AlertsBrick,
        #     bricks.ActionsOnTimeBrick,
        #     bricks.ActionsNotOnTimeBrick,
        #     bricks.UserMessagesBrick,
        # )
        brick_registry.register(
            (
                brick_registry.Tag.DETAIL,
                brick_registry.Tag.HOME,
                brick_registry.Tag.MY_PAGE,
            ),

            bricks.TodosBrick,
            bricks.MemosBrick,
            bricks.AlertsBrick,
            bricks.ActionsOnTimeBrick,
            bricks.ActionsNotOnTimeBrick,
            bricks.UserMessagesBrick,
        )

    @override
    def register_enumerable(self, enumerable_registry):
        from creme.creme_core.core import enumerable

        from . import models

        enumerable_registry.register_field(
            models.UserMessage, 'priority', enumerable.QSEnumerator
        )

    @override
    def register_fields_config(self, fields_config_registry):
        from . import models

        fields_config_registry.register_models(
            models.ToDo,
            models.Alert,
            # models.Action, TODO ?
            models.Memo,
        )

    @override
    def register_function_fields(self, function_field_registry):
        from creme.creme_core.models import CremeEntity

        from . import function_fields as ffields

        function_field_registry.register(
            CremeEntity,
            ffields.AlertsField,
            ffields.MemosField,
            ffields.TodosField,
        )

    @override
    def register_creme_config(self, config_registry):
        from . import models

        config_registry.register_model(models.UserMessagePriority, model_name='message_priority')

    @override
    def register_notification(self, notification_registry):
        from . import notification

        notification_registry.register_channel_types(
            notification.UserMessagesChannelType,
        ).register_content(
            content_cls=notification.AlertReminderContent,
        ).register_content(
            content_cls=notification.TodoReminderContent,
        ).register_content(
            content_cls=notification.MessageSentContent,
        )

    @override
    def register_reminders(self, reminder_registry):
        from . import reminders

        reminder_registry.register(
            reminders.ReminderAlert,
        ).register(
            reminders.ReminderTodo,
        )

    @override
    def register_setting_keys(self, setting_key_registry):
        from .setting_keys import todo_reminder_key

        setting_key_registry.register(todo_reminder_key)
