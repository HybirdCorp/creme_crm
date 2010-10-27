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

from creme_core.models import Lock

from emails.models.mail import EntityEmail, MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR

LOCK_NAME = "entity_emails_send"

#NB: python manage.py entity_emails_send

class Command(BaseCommand):
    help = "Send all unsended mails that have to be."

    def handle(self, *args, **options):
        lock = Lock.objects.filter(name=LOCK_NAME)

        if not lock:
            try:
                lock = Lock(name=LOCK_NAME)
                lock.save()

                for email in EntityEmail.objects.filter(status__in=[MAIL_STATUS_NOTSENT, MAIL_STATUS_SENDINGERROR]):
                    email.send()
                    
            finally:
                lock.delete()
        else:
            print 'A process is already running'
