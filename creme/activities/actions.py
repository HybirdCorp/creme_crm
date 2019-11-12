# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2019  Hybird
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

from creme import activities
from creme.creme_core.gui.actions import BulkEntityAction

Activity = activities.get_activity_model()


class BulkExportICalAction(BulkEntityAction):
    id = BulkEntityAction.generate_id('activities', 'export_ical')
    type = 'activities-export-ical'

    model = Activity
    label = _('Download in iCalendar format')
    icon = 'calendar_ical'
    url_name = 'activities__dl_ical'
