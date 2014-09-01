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

from creme.creme_core.core.reminder import reminder_registry
from creme.creme_core.core.setting_key import setting_key_registry
from creme.creme_core.registry import creme_registry
from creme.creme_core.gui.block import block_registry

from .blocks import alerts_block, actions_it_block, actions_nit_block, memos_block, todos_block, messages_block
from .reminders import reminder_alert, reminder_todo
from .setting_keys import todo_reminder_key


creme_registry.register_app('assistants', _(u'Assistants (Todos, Memo, ...)'), '/')
block_registry.register(todos_block, memos_block, alerts_block, actions_it_block, actions_nit_block, messages_block)

reminder_registry.register(reminder_alert)
reminder_registry.register(reminder_todo)

setting_key_registry.register(todo_reminder_key)
