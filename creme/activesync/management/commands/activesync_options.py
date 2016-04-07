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

from django.core.management.base import BaseCommand

import restkit


class Command(BaseCommand):
    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument('-u', '--url', action='store', dest='url')
        add_argument('-i', '--hotmail', action='store_const', dest='action',
                     const='https://m.hotmail.com/Microsoft-Server-ActiveSync',
                    )
        add_argument('-g', '--google', action='store_const', dest='action',
                     const='https://m.google.com/Microsoft-Server-ActiveSync',
                    )

    def handle(self, *args, **options):
        get_opt = options.get
        url = get_opt('url')
        action = get_opt('action')
        verbosity = get_opt('verbosity')

        if not url and not action:
            self.stderr.write('Url or action is required')
            return

        if action:
            url = action

        response = restkit.request(url, method='OPTIONS')

        if verbosity:
            for header in response.response.headers:
                self.stdout.write(header)
        else:
            targets = ('MS-ASProtocolVersions', 'MS-ASProtocolCommands')
            self.stdout.write('\n')
            for item in filter(lambda i: i[0] in targets, response.response.headers):
                self.stdout.write(item)

            self.stdout.write('\n')
