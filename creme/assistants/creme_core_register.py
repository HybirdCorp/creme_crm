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

from creme_core.gui.block import block_registry

from assistants.blocks import alerts_block, actions_it_block, actions_nit_block, memos_block, todos_block


reg_block = block_registry.register
reg_block(todos_block)
reg_block(memos_block)
reg_block(alerts_block)
reg_block(actions_it_block)
reg_block(actions_nit_block)

#from creme_core.reminder import reminder_registry
#from reminders import reminder_alert, reminder_todo
#reg_reminder = reminder_registry.register
#reg_reminder (reminder_alert)
#reg_reminder (reminder_todo)
