# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

import sys
#from optparse import make_option, OptionParser

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from creme.activesync.errors import CremeActiveSyncError
from creme.activesync.sync import Synchronization


USER_ID = 'user_id'
ALL_USERS = 'all_users'


class Command(BaseCommand):
    help = """Synchronise data with the ActiveSync server.
Use it only for debugging purpose, because the synchronization work should be done by the Job system (see creme_jobs.py)
"""

#    option_list = BaseCommand.option_list + (
#        make_option("-u", "--user_id", action="store",      dest=USER_ID,   help="Synchronised the user with the given id"),
#        make_option("-a", "--all",     action="store_true", dest=ALL_USERS, help="Synchronise all users (incompatible with --user_id option)", default=False),
#    )

    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument('-u', '--user_id',
                     action='store', dest=USER_ID,
                     help='Synchronised the user with the given id',
                    )
        add_argument('-a', '--all',
                     action='store_true', dest=ALL_USERS, default=False,
                     help='Synchronise all users (incompatible with --user_id option)  [default: %(default)s]',
                    )

#    def create_parser(self, prog_name, subcommand):
#        """
#        Create and return the ``OptionParser`` which will be used to
#        parse the arguments to this command.
#        """
#        return OptionParser(prog=prog_name,
#                            usage=self.usage(subcommand),
#                            version=self.get_version(),
#                            option_list=self.option_list,
#                            conflict_handler="resolve",
#                           )

    def _exit(self, msg):
        self.stderr.write(msg)
        sys.exit(2)

    def handle(self, *args, **options):
        get_option = options.get
        all_users = get_option(ALL_USERS)
        user_id   = get_option(USER_ID)
        User = get_user_model()

        if all_users:
            if user_id:
                self._exit('--all and --user_id options are not compatible')

            users = User.objects.all()
        else:
            if not user_id:
                self._exit('A user_id is required (or use --all option for all users)')

            try:
                users = [User.objects.get(pk=user_id)]
            except User.DoesNotExist:
                self._exit('%s is not a valid user_id.' % user_id)

        for user in users:
            try:
                Synchronization(user).synchronize()
            except CremeActiveSyncError as e:
                self.stderr.write(u"Error with user %s : %s" % (user, e))
