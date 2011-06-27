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

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


LOCK_NAME = "synchronizing_emails"

#NB: python manage.py emails_synchronize

class Command(BaseCommand):
    help = "Synchronize all externals mails sent to Creme into Creme."

    def handle(self, *args, **options):
        from creme_core.models.lock import Mutex, MutexLockedException
        from crudity.views.email import _fetch_emails

        try:
            lock = Mutex.get_n_lock(LOCK_NAME)

        except MutexLockedException, e:
            print 'A process is already running'

        else:
            try:
                user = User.objects.get(pk=settings.CREME_GET_EMAIL_JOB_USER_ID)
                print "There are %s new message(s)" % _fetch_emails(user)

            except User.DoesNotExist:
                pass
        finally:
            Mutex.graceful_release(LOCK_NAME)

