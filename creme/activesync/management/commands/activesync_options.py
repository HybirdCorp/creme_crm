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

from optparse import make_option, OptionParser

from django.core.management.base import BaseCommand

import restkit

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-u", "--url", action="store", dest="url"),
        make_option("-i", "--hotmail", action="store_const", const="https://m.hotmail.com/Microsoft-Server-ActiveSync", dest="action"),
        make_option("-g", "--google", action="store_const", const="https://m.google.com/Microsoft-Server-ActiveSync", dest="action"),
        make_option("-v", "--verbose", action="store_const", dest="verbose", const="false"),
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
        url = options.get('url')
        action = options.get('action')
        verbose = options.get('verbose')

        if not url and not action:
            print u"Url or action is required"
            return

        if action:
            url = action

        response=restkit.request(url, method='OPTIONS')

        if verbose:
            for header in response.response.headers:
                print header
        else:
            targets = ('MS-ASProtocolVersions', 'MS-ASProtocolCommands')
            print '\n'
            for item in filter(lambda i: i[0] in targets, response.response.headers):
                print item
            print '\n'