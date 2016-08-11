# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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
import logging
import urllib2

from functools import partial
from urlparse import urlparse
from StringIO import StringIO
from zipfile import ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
# from django.db.models.query_utils import Q
from django.template.defaultfilters import slugify

from creme.creme_core.utils import safe_unicode
from creme.creme_core.utils.chunktools import iter_as_chunk

from creme.persons import get_address_model

from ...models import Town, GeoAddress

logger = logging.getLogger(__name__)


class CSVPopulatorError(Exception):
    pass


class CSVPopulator(object):
    class ProtocolError(CSVPopulatorError):
        pass

    class ReadError(CSVPopulatorError):
        pass

    class ParseError(CSVPopulatorError):
        pass

    class Context(object):
        def __init__(self, defaults):
            self.line = 1
            self.defaults = defaults

    def __init__(self, columns, defaults=None, chunksize=50):
        """Constructor
        @param header: Names of columns to extract from CSV file.
                       Raises an error if a column is neither in file nor in defaults.
        @param defaults: dict of default values.
        @param chunksize: Number of lines in same transaction.
                          By default sqlite supports 999 entries for each transaction,
                          so use 999/fields as max chunksize value.
        """
        self.columns = columns
        self.defaults = defaults or {}
        self.chunksize = chunksize

    def _open(self, url):
        try:
            url_info = urlparse(url)

            if url_info.scheme in ('file', ''):
                input = open(url_info.path, 'rb')  # binary mode in order to avoid surprises with windows.
            elif url_info.scheme in ('http', 'https'):
                self.info('Downloading database...')
                input = urllib2.urlopen(url)
            else:
                raise self.ProtocolError('Unable to open CSV data from %s : unsupported protocol.' % url)

            if url_info.path.endswith('.zip'):
                archive = ZipFile(StringIO(input.read()))
                input = archive.open(archive.namelist()[0])

            return csv.reader(input)
        except CSVPopulatorError as e:
            raise e
        except Exception as e:
            raise self.ReadError('Unable to open CSV data from %s : %s' % (url, e))

    def _mapper(self, header):
        columns = self.columns
        defaults = self.defaults

        column_keys = frozenset(h.lower() for h in columns)
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
            raise self.ParseError("Following columns are missing and haven't got any default value : %s" % missings)

        def _aux(row):
            data = {key: row[index] or defaults.get(key) for key, index in indices}
            data.update(constants)
            return data

        return _aux

    def create(self, row, context):
        raise NotImplemented()

    def save(self, entries, context):
        raise NotImplemented()

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
        if isinstance(source, basestring):
            reader = self._open(source)
        else:
            reader = iter(source)

        mapper = self._mapper(reader.next())
        context = self.Context(self.defaults)

        for rows in iter_as_chunk(reader, self.chunksize):
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

            for entry in updated:
                entry.save(force_update=True)


class CSVTownPopulator(CSVPopulator):
    def __init__(self, defaults=None, chunksize=100):
        super(CSVTownPopulator, self).__init__(['title', 'zipcode', 'latitude', 'longitude', 'country'],
                                               defaults=defaults,
                                               chunksize=chunksize)

    def line_error(self, e, row, context):
        logger.error('    invalid data (line %d) : %s', context.line, e)

    def chunk_error(self, e, rows, context):
#         from creme.creme_core.utils import print_traceback
#         print_traceback()
        logger.error('    invalid data chunk : %s', e)

    def create(self, row, context):
        zipcodes = row['zipcode'].split('-')
        name, latitude, longitude = safe_unicode(row['title']), row['latitude'], row['longitude']
        slug = slugify(name)
        country = safe_unicode(row['country'])

        build_town = partial(Town, country=country)

        return [build_town(name=name,
                           slug=slug,
                           zipcode=zipcode,
                           latitude=latitude,
                           longitude=longitude,
                          ) for zipcode in zipcodes
               ]

    def save(self, entries, context):
        existings = dict(Town.objects.filter(zipcode__in=(t.zipcode for t in entries),
                                             slug__in=(t.slug for t in entries))
                                     .values_list('zipcode', 'pk'))

        find_pk = lambda town: existings.get(town.zipcode)

        self.sync(Town, entries, find_pk)


class Command(BaseCommand):
    def add_arguments(self, parser):
        add_argument = parser.add_argument
        add_argument('-p', '--populate', action='store_true', dest='populate', help='Populate addresses', default=False)
        add_argument('-s', '--stat', action='store_true', dest='stats', help='Display geolocation database stats', default=False)
        add_argument('-i', '--import', action='store_true', dest='import', default=False,
                     help='Import towns configured in GEOLOCATION_TOWNS setting',
                    )

    def sysout(self, message, visible):
        if visible:
            self.stdout.write(safe_unicode(message))

    def syserr(self, message):
        self.stderr.write(safe_unicode(message))

    def populate_addresses(self, verbosity=0):
        self.sysout('Populate geolocation information of addresses...', verbosity > 0)
        # GeoAddress.populate_geoaddresses(get_address_model().objects.filter(Q(zipcode__isnull=False) | Q(city__isnull=False)))
        GeoAddress.populate_geoaddresses(get_address_model().objects.exclude(zipcode='', city=''))

    def import_town_database(self, url, defaults):
        try:
            CSVTownPopulator(defaults=defaults).populate(url)
        except Exception as e:
            self.syserr(e)

    def import_town_all(self, verbosity=0):
        self.sysout('Importing Towns database...', verbosity > 0)

        for url, defaults in settings.GEOLOCATION_TOWNS:
            self.sysout(url, verbosity > 1)
            self.import_town_database(url, defaults)

    def print_stats(self):
        self.sysout('%d town(s) in database.' % Town.objects.count())

    def handle(self, *args, **options):
        populate = options.get('populate')
        stats = options.get('stats')
        imports = options.get('import')
        verbosity = options.get('verbosity')

        if stats:
            self.print_stats()

        if imports:
            self.import_town_all(verbosity)

        if populate:
            self.populate_addresses(verbosity)
