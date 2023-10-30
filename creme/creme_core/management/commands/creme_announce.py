################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from datetime import datetime
from time import strptime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import make_aware, now

from creme.creme_core.constants import UUID_CHANNEL_SYSTEM
from creme.creme_core.models import Notification
from creme.creme_core.notification import UpgradeAnnouncement


class Command(BaseCommand):
    help = 'Send a notification to announce a system upgrade.'

    DT_FORMAT = '%Y-%m-%dT%H:%M'

    def add_arguments(self, parser):
        parser.add_argument(
            'start',
            help=f"Date-time of the system upgrade (it's displayed in the notification). "
                 f"Format is '{self.DT_FORMAT.replace('%','%%')}'. "
                 f"Example: '{now().strftime(self.DT_FORMAT)}'.",
        )
        parser.add_argument(
            '--message', '-m', dest='message', help='Optional extra message.'
        )

    def handle(self, **options):
        # verbosity = options.get('verbosity')
        try:
            start = make_aware(datetime(*strptime(options['start'], self.DT_FORMAT)[:6]))
        except ValueError:
            raise CommandError('The date is invalid')

        Notification.objects.send(
            channel=UUID_CHANNEL_SYSTEM,
            # NB: excluding team is just an optimization, send() expands them
            # TODO: exclude staff in send() ?
            users=[
                *get_user_model().objects
                                 .filter(is_team=False, is_active=True)
                                 .exclude(is_staff=True)
            ],
            content=UpgradeAnnouncement(
                start=start, message=options.get('message', ''),
            ),
        )
