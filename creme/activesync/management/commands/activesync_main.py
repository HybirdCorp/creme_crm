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
import sys
from optparse import make_option, OptionParser
from django.contrib.auth.models import User

from django.core.management.base import BaseCommand

from activesync.sync import Synchronization

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-u", "--user_id", action="store", dest="user_id"),
    )

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``OptionParser`` which will be used to
        parse the arguments to this command.
        """
        return OptionParser(prog=prog_name,
                            usage=self.usage(subcommand),
                            version=self.get_version(),
                            option_list=self.option_list,
                            conflict_handler="resolve")

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        if not user_id:
            print "A user_id is required"
            sys.exit(2)

        try:
            user = User.objects.get(pk=user_id)
        except:
            print "%s is not a valid user_id." % user_id
            sys.exit(2)
        else:
            sync = Synchronization(user)
            sync.synchronize()
