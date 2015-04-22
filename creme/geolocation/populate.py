# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2015  Hybird
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
from StringIO import StringIO
from urlparse import urlparse
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.query_utils import Q
from django.template.defaultfilters import slugify

from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import BlockDetailviewLocation, BlockMypageLocation, SettingValue
from creme.creme_core.utils import safe_unicode
from creme.creme_core.utils.chunktools import iter_as_chunk

from creme.persons import get_contact_model, get_organisation_model, get_address_model
#from creme.persons.models import Contact, Organisation, Address

from .blocks import persons_maps_block, persons_filter_maps_block, who_is_around_maps_block
from .constants import DEFAULT_SEPARATING_NEIGHBOURS
from .models import Town, GeoAddress
from .setting_keys import NEIGHBOURHOOD_DISTANCE


logger = logging.getLogger(__name__)

class CSVPopulator(object):
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
                          (This limitation will disappear with Django 1.5)
        """
        self.columns = columns
        self.defaults = defaults or {}
        self.chunksize = chunksize

    def _open(self, url):
        try:
            url_info = urlparse(url)

            if url_info.scheme in ('file', ''):
                input = open(url_info.path, 'rb') # binary mode in order to avoid surprises with windows.
            elif url_info.scheme in ('http', 'https'):
                logger.info('Downloading database...')
                input = urllib2.urlopen(url)
            else:
                raise Exception('unsupported protocol %s' % url_info.scheme)

            if url_info.path.endswith('.zip'):
                archive = ZipFile(StringIO(input.read()))
                input = archive.open(archive.namelist()[0])

            return csv.reader(input)
        except Exception as e:
            raise Exception('Unable to open CSV data from %s : %s' % (url, e))

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
            raise Exception("Following columns are missing and haven't got any default value : %s" % missings)

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

        create_town = partial(Town, country=country)

        return [create_town(name=name,
                            slug=slug,
                            zipcode=zipcode,
                            latitude=latitude,
                            longitude=longitude
                           ) for zipcode in zipcodes
               ]

    def save(self, entries, context):
        existings = dict(Town.objects.filter(zipcode__in=(t.zipcode for t in entries),
                                             slug__in=(t.slug for t in entries))
                                     .values_list('zipcode', 'pk'))
        created = []
        updated = []

        for t in entries:
            if t.zipcode in existings:
                t.pk = existings[t.zipcode]
                updated.append(t)
            else:
                created.append(t)

        with transaction.atomic():
            Town.objects.bulk_create(created)

            for town in updated:
                town.save(force_update=True)


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate_towns(self, iterable, defaults):
        CSVTownPopulator(defaults=defaults).populate(iterable)

    def import_towns(self, url, defaults):
        try:
            logger.info('Importing Towns database...')
            self.populate_towns(url, defaults)
        except Exception as e:
            logger.warn(e)

    def populate_addresses(self):
#        GeoAddress.populate_geoaddresses(Address.objects.filter(Q(zipcode__isnull=False) | Q(city__isnull=False)))
        GeoAddress.populate_geoaddresses(get_address_model().objects.filter(Q(zipcode__isnull=False) | Q(city__isnull=False)))

    def populate(self):
        already_populated = SettingValue.objects.filter(key_id=NEIGHBOURHOOD_DISTANCE.id).exists()

        SettingValue.create_if_needed(key=NEIGHBOURHOOD_DISTANCE, user=None, value=DEFAULT_SEPARATING_NEIGHBOURS)

        if not already_populated or not Town.objects.exists():
            for url, defaults in settings.GEOLOCATION_TOWNS:
                self.import_towns(url, defaults)

        logger.info('Populating geolocations of existing addresses...')
        self.populate_addresses()

        if not already_populated:
            Contact = get_contact_model()
            Organisation = get_organisation_model()

            BlockDetailviewLocation.create(block_id=persons_maps_block.id_, order=70, zone=BlockDetailviewLocation.LEFT, model=Organisation)
            BlockDetailviewLocation.create(block_id=persons_maps_block.id_, order=70, zone=BlockDetailviewLocation.LEFT, model=Contact)
            BlockDetailviewLocation.create(block_id=who_is_around_maps_block.id_, order=600, zone=BlockDetailviewLocation.BOTTOM, model=Organisation)
            BlockDetailviewLocation.create(block_id=who_is_around_maps_block.id_, order=600, zone=BlockDetailviewLocation.BOTTOM, model=Contact)

            BlockMypageLocation.create(block_id=persons_filter_maps_block.id_, order=20)

            # add this bloc only if the root user exists (creme_core populated)
            root = get_user_model().objects.filter(pk=1).first()
            if root:
                logger.info('Creme core is installed => the block PersonsFilterMap can be activated')
                BlockMypageLocation.create(block_id=persons_filter_maps_block.id_, order=8, user=root)
