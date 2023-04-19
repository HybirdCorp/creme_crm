################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2023-2025  Hybird
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

import json
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from creme.creme_config.constants import FILE_VERSION
from creme.creme_config.core.importers import IMPORTERS


class Command(BaseCommand):
    help = 'Import the JSON file created by the command "creme_config_export"'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Path of the JSON file.')

    def handle(self, **options):
        # TODO: factorise with ImportForm
        path = options.get('file')

        try:
            with open(path) as f:
                deserialized_data = json.load(f)
        except Exception as e:
            raise CommandError(f'error when opening the file ({e})') from e

        if not isinstance(deserialized_data, dict):
            raise CommandError(_('main content must be a dictionary'))

        if deserialized_data.get('version') != FILE_VERSION:
            raise CommandError(_('The file has an unsupported version.'))

        importers = IMPORTERS.build_importers()
        validated_data = defaultdict(set)

        try:
            for importer in importers:
                importer.validate(
                    deserialized_data=deserialized_data,
                    validated_data=validated_data,
                )

            for importer in importers:
                importer.save()
        except Exception as e:
            # TODO: test
            raise CommandError(f'error when importing data ({e})') from e
