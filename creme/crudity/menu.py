# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from creme.creme_core.gui.menu import FixedURLEntry


class WaitingActionsEntry(FixedURLEntry):
    id = 'crudity-waiting_actions'
    label = _('Waiting actions')
    permissions = 'crudity'
    url_name = 'crudity__actions'


class CrudityHistoryEntry(FixedURLEntry):
    id = 'crudity-history'
    label = _('History')
    permissions = 'crudity'
    url_name = 'crudity__history'
