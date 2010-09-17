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

from creme_settings import CREME_GET_EMAIL_JOB_USER_ID
from creme_core.models import Lock
from creme.emails.models.mail import EntityEmail



LOCK_NAME = "synchronizing_emails"

#NB: python manage.py emails_synchronize

class Command(BaseCommand):
    help = "Synchronize all externals mails sent to Creme into Creme."

    def handle(self, *args, **options):
        lock = Lock.objects.filter(name=LOCK_NAME)

        if not lock:
            try:
                lock = Lock(name=LOCK_NAME)
                lock.save()

                EntityEmail.fetch_mails(CREME_GET_EMAIL_JOB_USER_ID)
            finally:
                lock.delete()
        else:
            print 'A process is already running'
