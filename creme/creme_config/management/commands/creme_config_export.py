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

from json import dumps as json_dump

from django.core.management.base import BaseCommand, CommandError

from creme.creme_config.core.exporters import EXPORTERS
from creme.creme_core.core.exceptions import ConflictError


class Command(BaseCommand):
    help = (
        'Export the configuration as a JSON file '
        '(see the command "creme_config_import" to import this file). '
        'Exported configuration: '
        'roles, blocks, buttons, search,  property & relationship types, '
        'custom fields, views of list, filters.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--indent', '-i', default=1, type=int, help='Indentation if the JSON file.',
        )
        # TODO: output file?
        # TODO: other type of output (xml, toml, ini...)?

    def handle(self, **options):
        indent = options.get('indent')

        try:
            info = EXPORTERS.export()
        except ConflictError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(json_dump(info, indent=indent, separators=(',', ': ')))
