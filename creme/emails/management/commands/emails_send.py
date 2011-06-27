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

from logging import debug
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings


LOCK_NAME = "sending_emails"

#NB: python manage.py emails_send

class Command(BaseCommand):
    help = "Send all unsended mails that have to be."

    def handle(self, *args, **options):
        from creme_core.models.lock import Mutex, MutexLockedException
        from emails.models import EmailSending
        from emails.models.sending import SENDING_TYPE_IMMEDIATE, SENDING_STATE_DONE, SENDING_STATE_INPROGRESS, SENDING_STATE_PLANNED

        try:
            lock = Mutex.get_n_lock(LOCK_NAME)

        except MutexLockedException, e:
            print 'A process is already running'

        else:
            #for sending in EmailSending.objects.filter(state=SENDING_STATE_PLANNED):
            for sending in EmailSending.objects.exclude(state=SENDING_STATE_DONE):
                if SENDING_TYPE_IMMEDIATE == sending.type or sending.sending_date <= datetime.now():
                    sending.state = SENDING_STATE_INPROGRESS
                    sending.save()

#                        if getattr(settings, 'REMOTE_STATS', False):
#                            from emails.utils.remoteutils import populate_minicreme #broken
#                            populate_minicreme(sending)

                    status = sending.send_mails()

                    sending.state = status or SENDING_STATE_DONE
                    sending.save()
        finally:
            Mutex.graceful_release(LOCK_NAME)
