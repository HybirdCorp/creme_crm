# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.core.management.base import BaseCommand
from django.core.management.commands.test import Command as TestCommand


class Command(BaseCommand):
    help = 'Run tests for installed (Creme) apps.'
    args = ''
    option_list = TestCommand.option_list

    def handle(self, *args, **options):
        ##TestCommand().handle(*settings.INSTALLED_CREME_APPS, **options)
        #TestCommand().handle(*[app.replace('creme.', '') for app in settings.INSTALLED_CREME_APPS], **options)

        apps = settings.INSTALLED_CREME_APPS

        try:
            TestCommand().handle(*[app + '.tests' for app in apps], **options)
        except AttributeError as e:
            if "'tests'" in e.message:
                from imp import find_module

                self.stderr.write('It seems one of your apps does not have a "tests" module...')
                invalid_apps = []

                for app in apps:
                    try:
                        find_module("tests", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
                    except ImportError:
                        invalid_apps.append(app)

                if invalid_apps:
                    self.stderr.write('... invalid apps are: %s' % invalid_apps)
                    return
                else:
                    self.stderr.write('... no invalid app found, so the truth is out.')

            raise e
