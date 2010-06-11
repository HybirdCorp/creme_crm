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

from django.core.management.base import BaseCommand

from creme_core import autodiscover
from creme_core.reminder import reminder_registry


class Command(BaseCommand):
    help = 'Populates the Creme DB with the script given by parameter.'
    args = 'script_name'

    def handle(self, *app_labels, **options):
        print 'Reminder Commands'
        autodiscover()
        for one_remind in reminder_registry.itervalues():
            one_remind.execute()

