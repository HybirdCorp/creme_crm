# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2022  Hybird
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

import csv
import io
import logging
from functools import partial
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.template.defaultfilters import slugify

from creme.creme_core.utils.chunktools import iter_as_chunk
from creme.creme_core.utils.collections import OrderedSet
from creme.creme_core.utils.url import parse_path
from creme.persons import get_address_model

from ...models import GeoAddress, Town

logger = logging.getLogger(__name__)


class CSVPopulatorError(Exception):
    pass


class CSVPopulator:
    class ProtocolError(CSVPopulatorError):
        pass

    class ReadError(CSVPopulatorError):
        pass

    class ParseError(CSVPopulatorError):
        pass

    class Context:
        def __init__(self, defaults):
            self.line = 1
            self.defaults = defaults

    def __init__(self, columns, defaults=None, chunksize=50):
        """Constructor.
        @param columns: Names of columns to extract from CSV file.
               Raises an error if a column is neither in file nor in defaults.
        @param defaults: dict of default values.
        @param chunksize: Number of lines in same transaction.
               By default sqlite supports 999 entries for each transaction,
               so use 999/fields as max chunksize value.
        """
        self.columns = columns
        self.defaults = defaults or {}
        self.chunksize = chunksize

    def _get_source_file(self, url_info):
        if url_info.scheme in {'file', ''}:
            self.info(f'Reading database from {url_info.geturl()}...')
            return open(url_info.path, 'rb')
        elif url_info.scheme in {'http', 'https'}:
            self.info(f'Downloading database from {url_info.geturl()}...')
            return urlopen(url_info.geturl())
        else:
            raise self.ProtocolError(
                f'Unable to open CSV data from {url_info.geturl()} : '
                f'unsupported protocol.'
            )

    def _mapper(self, header):
        columns = self.columns
        defaults = self.defaults

        column_keys = OrderedSet(h.lower() for h in columns)  # TODO: OrderedFrozenSet
        row_keys = frozenset(k.lower() for k in header)

        missings = []
        constants = {}
        indices = [(key, index) for index, key in enumerate(header) if key in column_keys]

        for key in column_keys:
            if key not in row_keys:
                try:
                    constants[key] = defaults[key]
                except KeyError:
                    missings.append(key)

        if missings:
            raise self.ParseError(
                f"Following columns are missing and haven't got any default value : {missings}"
            )

        def _aux(row):
            data = {key: row[index] or defaults.get(key) for key, index in indices}
            data.update(constants)
            return data

        return _aux

    def create(self, row, context):
        raise NotImplementedError

    def save(self, entries, context):
        raise NotImplementedError

    def pre(self, rows, context):
        pass

    def post(self, entries, context):
        pass

    def line_error(self, e, row, context):
        pass

    def chunk_error(self, e, rows, context):
        pass

    def info(self, message):
        logger.info(message)

    def populate(self, source):
        if isinstance(source, Path):
            source = source.resolve().as_uri()

        if isinstance(source, str):
            try:
                url_info = parse_path(source)

                with self._get_source_file(url_info) as bytes_input:
                    if url_info.path.endswith('.zip'):
                        archive = ZipFile(
                            bytes_input
                            if bytes_input.seekable() else
                            io.BytesIO(bytes_input.read())
                        )

                        with archive.open(archive.namelist()[0]) as zipped_bytes_input:
                            self._populate_from_bytes(zipped_bytes_input)
                    else:
                        self._populate_from_bytes(bytes_input)
            except CSVPopulatorError:
                raise
            except Exception as e:
                raise self.ReadError(f'Unable to open CSV data from {source} : {e}') from e
        elif hasattr(source, '__iter__'):
            self._populate_from_lines(iter(source))
        else:
            raise ValueError('The source must be a path or an iterable.')

    def _populate_from_bytes(self, bytes_input):
        with io.TextIOWrapper(bytes_input) as wrapped_bytes_input:
            self._populate_from_lines(csv.reader(wrapped_bytes_input))

    def _populate_from_lines(self, lines):
        mapper = self._mapper(next(lines))
        context = self.Context(self.defaults)

        for rows in iter_as_chunk(lines, self.chunksize):
            entries = []

            if mapper:
                rows = [mapper(row) for row in rows]

            try:
                self.pre(rows, context)

                for row in rows:
                    try:
                        entries.extend(self.create(row, context))
                    except Exception as e:
                        self.line_error(e, row, context)

                    context.line += 1

                self.save(entries, context)
                self.post(entries, context)
            except Exception as e:
                self.chunk_error(e, rows, context)

    def sync(self, model, entries, build_pk):
        created = []
        updated = []

        for t in entries:
            pk = build_pk(t)

            if not pk:
                created.append(t)
            else:
                t.pk = pk
                updated.append(t)

        with transaction.atomic():
            model.objects.bulk_create(created)

            # TODO: bulk_update() ?
            for entry in updated:
                entry.save(force_update=True)


class CSVTownPopulator(CSVPopulator):
    def __init__(self, defaults=None, chunksize=100):
        super().__init__(
            ['title', 'zipcode', 'latitude', 'longitude', 'country'],
            defaults=defaults, chunksize=chunksize,
        )

    def line_error(self, e, row, context):
        logger.error('    invalid data (line %d) : %s', context.line, e)

    def chunk_error(self, e, rows, context):
        logger.error('    invalid data chunk : %s', e)

    def create(self, row, context):
        zipcodes = row['zipcode'].split('-')

        name      = row['title']
        latitude  = row['latitude']
        longitude = row['longitude']

        slug = slugify(name)
        country = row['country']

        build_town = partial(Town, country=country)

        return [
            build_town(
                name=name,
                slug=slug,
                zipcode=zipcode,
                latitude=latitude,
                longitude=longitude,
            ) for zipcode in zipcodes
        ]

    def save(self, entries, context):
        get_existing_pk_by_zipcode = dict(
            Town.objects.filter(
                zipcode__in=(t.zipcode for t in entries),
                slug__in=(t.slug for t in entries),
            ).values_list('zipcode', 'pk')
        ).get

        self.sync(
            Town, entries,
            lambda town: get_existing_pk_by_zipcode(town.zipcode),
        )


class Command(BaseCommand):
    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument(
            '-p', '--populate', action='store_true', dest='populate',
            help='Populate addresses', default=False,
        )
        add_argument(
            '-s', '--stat', action='store_true', dest='stats',
            help='Display geolocation database stats', default=False,
        )
        add_argument(
            '-i', '--import', action='store_true', dest='import', default=False,
            help='Import towns configured in GEOLOCATION_TOWNS setting',
        )

    def sysout(self, message, visible):
        if visible:
            self.stdout.write(message)

    def syserr(self, message):
        self.stderr.write(message)

    def populate_addresses(self, verbosity=0):
        self.sysout('Populate geolocation information of addresses...', verbosity > 0)
        GeoAddress.populate_geoaddresses(
            get_address_model().objects.exclude(zipcode='', city='')
        )

    def import_town_database(self, url, defaults):
        try:
            CSVTownPopulator(defaults=defaults).populate(url)
        except Exception as e:
            self.syserr(str(e))

    def import_town_all(self, verbosity=0):
        self.sysout('Importing Towns database...', verbosity > 0)

        for url, defaults in settings.GEOLOCATION_TOWNS:
            self.sysout(url, verbosity > 1)
            self.import_town_database(url, defaults)

    def print_stats(self, verbosity=0):
        self.sysout(f'{Town.objects.count()} town(s) in database.', verbosity > 0)

    def handle(self, *args, **options):
        populate = options.get('populate')
        stats = options.get('stats')
        imports = options.get('import')
        verbosity = options.get('verbosity')

        if stats:
            self.print_stats(verbosity)

        if imports:
            self.import_town_all(verbosity)

        if populate:
            self.populate_addresses(verbosity)
