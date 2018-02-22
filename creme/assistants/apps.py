# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class AssistantsConfig(CremeAppConfig):
    name = 'creme.assistants'
    verbose_name = _(u'Assistants (Todos, Memo, ...)')
    dependencies = ['creme.creme_core']

    def ready(self):
        super(AssistantsConfig, self).ready()

        from . import signals

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.TodosBrick,
                                bricks.MemosBrick,
                                bricks.AlertsBrick,
                                bricks.ActionsOnTimeBrick,
                                bricks.ActionsNotOnTimeBrick,
                                bricks.UserMessagesBrick,
                               )

    def register_reminders(self, reminder_registry):
        from . import reminders

        reg_reminder = reminder_registry.register
        reg_reminder(reminders.reminder_alert)
        reg_reminder(reminders.reminder_todo)

    def register_setting_keys(self, setting_key_registry):
        from .setting_keys import todo_reminder_key

        setting_key_registry.register(todo_reminder_key)
