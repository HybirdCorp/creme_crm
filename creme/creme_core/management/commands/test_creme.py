# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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
from django.core.management.commands.test import Command as TestCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Run tests for installed apps.'
    args = ''
    option_list = TestCommand.option_list

    def handle(self, *args, **options):
        TestCommand().handle(*settings.INSTALLED_CREME_APPS, **options)
