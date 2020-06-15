# -*- coding: utf-8 -*-

################################################################################
#
# Copyright (c) 2018-2020 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from django.core.management.base import BaseCommand
from django.urls import NoReverseMatch, reverse

from creme.creme_core.conf.urls import swap_manager


class Command(BaseCommand):
    help = 'Check all Swappable(url()) of your project ' \
           '(made for trunk developers ; you probably never need to run it)'

    def handle(self, **options):
        verbosity = options.get('verbosity')
        errors_count = 0

        for group in swap_manager:
            for swappable in group:
                name = swappable.pattern.name

                try:
                    reverse(viewname=name, args=swappable.check_args)
                except NoReverseMatch:
                    errors_count += 1
                    self.stderr.write(
                        f'The swappable URL "{name}" from the app "{group.app_name}" '
                        f'seems having broken check_args: {swappable.verbose_args}.'
                    )

        if verbosity:
            self.stdout.write(f'{errors_count} error(s) found.')
