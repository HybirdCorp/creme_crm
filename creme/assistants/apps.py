# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

    # def register_creme_app(self, creme_registry):
    #     creme_registry.register_app('assistants', _(u'Assistants (Todos, Memo, ...)'), '/')

    def register_blocks(self, block_registry):
        from .blocks import (alerts_block, actions_it_block, actions_nit_block,
                memos_block, todos_block, messages_block)

        block_registry.register(todos_block, memos_block, alerts_block,
                                actions_it_block, actions_nit_block,
                                messages_block,
                               )

    def register_reminders(self, reminder_registry):
        from .reminders import reminder_alert, reminder_todo

        reg_reminder = reminder_registry.register
        reg_reminder(reminder_alert)
        reg_reminder(reminder_todo)

    def register_setting_key(self, setting_key_registry):
        from .setting_keys import todo_reminder_key

        setting_key_registry.register(todo_reminder_key)
