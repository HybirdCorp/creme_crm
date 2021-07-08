# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019-2021  Hybird
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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from creme.activities.models import Calendar


class Command(BaseCommand):
    help = (
        'Create the default Calendars for users which do not have one. '
        'settings.ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC is used to determinate '
        'the wanted behaviour. '
        '(True/False => public/private ; None => no calendar created).'
    )

    def handle(self, **options):
        verbosity = options.get('verbosity')
        is_public = settings.ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC

        if is_public is None:
            if verbosity >= 1:
                self.stderr.write(
                    'ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC is None => no calendar created.'
                )
        elif isinstance(is_public, bool):
            users = get_user_model().objects.filter(
                is_staff=False, is_active=True,
                calendar__is_default__isnull=True,
            )

            for user in users:
                Calendar.objects.create_default_calendar(user=user, is_public=is_public)

            if verbosity >= 1:
                self.stdout.write(f'{len(users)} calendar(s) created.')
        else:
            if verbosity >= 1:
                self.stderr.write(
                    'ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC is invalid '
                    '(not in {None, True, False}) '
                    '=> no calendar created.'
                )
