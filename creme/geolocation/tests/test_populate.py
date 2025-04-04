import urllib
from functools import partial
from pathlib import Path
from unittest.mock import patch

from django.conf import settings

from creme.creme_core.tests.base import CremeTestCase
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..management.commands.geolocation import Command as GeolocationCommand
from ..management.commands.geolocation import CSVPopulator
from ..models import GeoAddress, Town
from .base import Address, GeoLocationBaseTestCase, Organisation


class MockCSVPopulator(CSVPopulator):
    def __init__(self, columns=None, defaults=None, chunksize=50):
        CSVPopulator.__init__(self, columns, defaults=defaults, chunksize=chunksize)
        self.mock_reset()

    def mock_reset(self):
        self.mock_saved = []
        self.mock_line_errors = []
        self.mock_chunk_errors = []

    def create(self, row, context):
        return [row]

    def save(self, entries, context):
        self.mock_saved.extend(entries)

    def line_error(self, e, row, context):
        self.mock_line_errors.append([str(e), row, context.line])

    def chunk_error(self, e, rows, context):
        self.mock_chunk_errors.append([str(e), rows])


class CSVPopulatorTestCase(CremeTestCase):
    def test_columns(self):
        populator = MockCSVPopulator(['name', 'code'])
        self.assertListEqual(populator.columns, ['name', 'code'])

        mapper = populator._mapper(['name', 'value', 'code'])
        self.assertDictEqual({'name': 'A', 'code': 15}, mapper(['A', 11200, 15]))

    def test_columns_defaults(self):
        """ default column exists in file header """
        populator = MockCSVPopulator(['name', 'code', 'value'], defaults={'value': 8})
        self.assertListEqual(populator.columns, ['name', 'code', 'value'])

        mapper = populator._mapper(['name', 'value', 'code'])
        self.assertDictEqual({'name': 'A', 'code': 15, 'value': 11200}, mapper(['A', 11200, 15]))
        self.assertDictEqual({'name': 'B', 'code': 28, 'value': 8},     mapper(['B', None,  28]))

    def test_columns_constants(self):
        """ default column doesn't exist in file header """
        populator = MockCSVPopulator(['name', 'code', 'value'], defaults={'value': 8})
        self.assertListEqual(populator.columns, ['name', 'code', 'value'])

        mapper = populator._mapper(['name', 'code'])
        self.assertDictEqual({'name': 'A', 'code': 15, 'value': 8}, mapper(['A', 15]))
        self.assertDictEqual({'name': 'B', 'code': 28, 'value': 8}, mapper(['B', 28]))

    def test_columns_missing_columns(self):
        populator = MockCSVPopulator(['name', 'code', 'other', 'value'])
        self.assertListEqual(populator.columns, ['name', 'code', 'other', 'value'])

        with self.assertRaises(CSVPopulator.ParseError) as error:
            populator._mapper(['name', 'other'])

        self.assertEqual(
            str(error.exception),
            "Following columns are missing and haven't got any default "
            "value: {}".format(['code', 'value'])
        )

    def test_chunk_error(self):
        class InvalidChunkCSVPopulator(MockCSVPopulator):
            def save(self, entries, context):
                raise Exception('invalid chunk !')

        populator = InvalidChunkCSVPopulator(['name', 'code'])

        data = (
            ['name', 'code', 'value'],
            ['A', 11200, 15],
            ['B', 45400, 23],
            ['C', 23000, 25],
        )

        populator.populate(data)

        self.assertListEqual(populator.mock_saved, [])
        self.assertListEqual(populator.mock_line_errors, [])
        self.assertListEqual(
            populator.mock_chunk_errors,
            [
                [
                    str(Exception('invalid chunk !')),
                    [
                        {'name': 'A', 'code': 11200},
                        {'name': 'B', 'code': 45400},
                        {'name': 'C', 'code': 23000},
                    ],
                ],
            ],
        )

    def test_line_error(self):
        class InvalidLineCSVPopulator(MockCSVPopulator):
            def create(self, row, context):
                if context.line % 2 > 0:
                    return super().create(row, context)

                raise Exception('invalid line !')

        populator = InvalidLineCSVPopulator(['name', 'code'])

        chunk = (
            ['name', 'code', 'value'],
            ['A', 11200, 15],
            ['B', 45400, 23],
            ['C', 23000, 25],
            ['D', 75880, 41],
        )

        populator.populate(chunk)

        self.assertListEqual(
            [
                {'name': 'A', 'code': 11200},
                {'name': 'C', 'code': 23000},
            ],
            populator.mock_saved,
        )
        self.assertListEqual(
            [
                [str(Exception('invalid line !')), {'name': 'B', 'code': 45400}, 2],
                [str(Exception('invalid line !')), {'name': 'D', 'code': 75880}, 4],
            ],
            populator.mock_line_errors,
        )
        self.assertListEqual(populator.mock_chunk_errors, [])

    def test_populate_from_missing_file(self):
        populator = MockCSVPopulator(['name', 'code'])
        name = 'unknown'

        with self.assertRaises(CSVPopulator.ReadError) as error:
            populator.populate(name)

        self.assertIn(f'Unable to open CSV data from {name}', str(error.exception))

    def test_populate_from_invalid_file(self):
        columns = ['name', 'code']
        populator = MockCSVPopulator([*columns])

        with self.assertRaises(CSVPopulator.ParseError) as error:
            populator.populate(str(
                Path(settings.CREME_ROOT) / 'geolocation' / 'apps.py'
            ))

        self.assertEqual(
            str(error.exception),
            f"Following columns are missing and haven't got any default value: {columns}",
        )

    def test_populate_from_invalid_protocol(self):
        populator = MockCSVPopulator(['name', 'code'])
        url = 'unknown://creme/geolocation/populate.py'

        with self.assertRaises(CSVPopulator.ProtocolError) as error:
            populator.populate(url)

        self.assertEqual(
            str(error.exception),
            f'Unable to open CSV data from {url} : unsupported protocol.'
        )

    def test_populate_from_file(self):
        populator = MockCSVPopulator(['name', 'code'])
        populator.populate(str(
            Path(settings.CREME_ROOT) / 'geolocation' / 'tests' / 'data' / 'valid.csv'
        ))

        self.assertListEqual(
            populator.mock_saved,
            [
                {'name': 'A', 'code': '44556'},
                {'name': 'B', 'code': '54122'},
                {'name': 'C', 'code': '75001'},
            ],
        )

    def test_populate_from_invalid_zip_file(self):
        populator = MockCSVPopulator(['name', 'code'])
        url = Path(settings.CREME_ROOT) / 'geolocation' / 'tests' / 'data' / 'not_archive.csv.zip'

        with self.assertRaises(CSVPopulator.ReadError) as error:
            populator.populate(str(url))

        self.assertEqual(
            str(error.exception),
            f'Unable to open CSV data from {url} : File is not a zip file'
        )

    def test_populate_from_zip_file(self):
        populator = MockCSVPopulator(['name', 'code'])
        populator.populate(str(
            Path(settings.CREME_ROOT) / 'geolocation' / 'tests' / 'data' / 'valid.csv.zip'
        ))

        self.assertListEqual(
            populator.mock_saved,
            [
                {'name': 'A', 'code': '44555'},
                {'name': 'B', 'code': '54122'},
                {'name': 'C', 'code': '75001'},
            ],
        )

    def test_populate_from_http(self):
        populator = MockCSVPopulator(['name', 'code'])

        csv_file = open(
            Path(settings.CREME_ROOT) / 'geolocation' / 'tests' / 'data' / 'valid.csv',
            mode='rb',
        )
        # NB: this url is not valid, we just use it to test called arguments.
        url = 'http://localhost:8001/geolocation/data/valid.csv'

        with patch('urllib.request.urlopen', return_value=csv_file) as urlopen_mock:
            with self.assertNoException():
                populator.populate(url)

        urlopen_mock.assert_called_once_with(url)

        self.assertListEqual(
            populator.mock_saved,
            [
                {'name': 'A', 'code': '44556'},
                {'name': 'B', 'code': '54122'},
                {'name': 'C', 'code': '75001'},
            ],
        )

    def test_populate_from_http_zip(self):
        populator = MockCSVPopulator(['name', 'code'])

        zip_file = open(
            Path(settings.CREME_ROOT) / 'geolocation' / 'tests' / 'data' / 'valid.csv.zip',
            mode='rb',
        )
        # NB: this url is not valid, we just use it to test called arguments.
        url = 'http://localhost:8001/geolocation/data/groland.csv.zip'

        with patch(
            'urllib.request.urlopen',
            return_value=zip_file,
        ) as urlopen_mock:
            with self.assertNoException():
                populator.populate(url)

        urlopen_mock.assert_called_once_with(url)

        self.assertListEqual(
            populator.mock_saved,
            [
                {'name': 'A', 'code': '44555'},
                {'name': 'B', 'code': '54122'},
                {'name': 'C', 'code': '75001'},
            ],
        )

    def test_http_error(self):
        populator = MockCSVPopulator(['name', 'code'])

        url = 'http://localhost:8001/geolocation/data/doesnotexist.csv'

        exception = urllib.error.URLError('page cannot be found')
        with patch('urllib.request.urlopen') as urlopen_mock:
            urlopen_mock.side_effect = exception

            with self.assertRaises(MockCSVPopulator.ReadError) as cm:
                populator.populate(url)

        urlopen_mock.assert_called_once_with(url)
        self.assertEqual(
            f'Unable to open CSV data from {url} : {exception}',
            str(cm.exception),
        )


class TownPopulatorTestCase(GeoLocationBaseTestCase):
    HEADER   = ['', '', '', 'name', '', 'title', '', '', 'zipcode', '', '', '', '', '', '', '', '', '', '', 'longitude', 'latitude', '', '', '', '', '', '']  # NOQA
    OZAN     = ["1", "01", "ozan", "OZAN", "ozan", "Ozan", "O250", "OSN", "01190", "284", "01284", "2", "26", "6", "618", "469", "500", "93", "6.6", "4.91667", "46.3833", "2866", "51546", "+45456", "462330", "170", "205"]  # NOQA
    PERON    = ["9", "01", "peron", "PERON", "peron", "Péron", "P650", "PRN", "01630", "288", "01288", "3", "12", "6", "2143", "1578", "1900", "82", "26.01", "5.93333", "46.2", "3989", "51322", "+55535", "461124", "411", "1501"]  # NOQA
    ACOUA    = ["36810", "976", "acoua", "ACOUA", "acoua", "Acoua", "A200", "AK", "97630", "601", "97601", "0", "01", None, "4714", "4714", "4714", "373", "12.62", "45.0645", "-12.7239", None, None, None, None, None, None]  # NOQA
    STBONNET = ["6307", "17", "saint-bonnet-sur-gironde", "SAINT-BONNET-SUR-GIRONDE", "saint bonnet sur gironde", "Saint-Bonnet-sur-Gironde", "S53153262653", "SNTBNTSRJRNT", "17150", "312", "17312", "1", "16", "6", "869", "838", "900", "28", "30.6", "-0.666667", "45.35", "-3329", "50394", "-03936", "452116", "0", "87"]  # NOQA
    INVALID  = ["36810", "976", "acoua", "ACOUA", "acoua", "Acoua", "A200", "AK", None, "601", "97601", "0", "01", None, "4714", "4714", "4714", "373", "12.62", "45.0645", "-12.7239", None, None, None, None, None, None]  # NOQA

    def setUp(self):
        super().setUp()
        self.command = GeolocationCommand()

    def assertTown(self, town, **kwargs):
        self.assertModelInstance(town, Town, **kwargs)

    def test_populate_does_not_exist(self):
        self.assertEqual(0, Town.objects.count())

        self.command.import_town_database(
            [self.HEADER, self.OZAN, self.PERON, self.ACOUA, self.STBONNET],
            {'country': 'France'},
        )
        self.assertEqual(4, Town.objects.count())

        get_town = partial(Town.objects.get, country='France')
        self.assertTown(
            get_town(zipcode='01190'),
            zipcode='01190', name='Ozan',  slug='ozan',  longitude=4.91667, latitude=46.3833,
        )
        self.assertTown(
            get_town(zipcode='01630'),
            zipcode='01630', name='Péron', slug='peron', longitude=5.93333, latitude=46.2,
        )
        self.assertTown(
            get_town(zipcode='97630'),
            zipcode='97630', name='Acoua', slug='acoua', longitude=45.0645, latitude=-12.7239,
        )
        self.assertTown(
            get_town(zipcode='17150'),
            zipcode='17150', name='Saint-Bonnet-sur-Gironde',
            slug='saint-bonnet-sur-gironde', longitude=-0.666667, latitude=45.35,
        )

    def test_populate_exists_updated(self):
        Town.objects.create(zipcode='01190', name='Ozan', slug='ozan', longitude=0.0, latitude=0.0)
        self.assertEqual(1, Town.objects.count())

        self.command.import_town_database(
            [self.HEADER, self.OZAN, self.PERON, self.ACOUA, self.STBONNET],
            {'country': 'FRANCE'}
        )
        self.assertEqual(4, Town.objects.count())

        get_town = Town.objects.get
        self.assertTown(
            get_town(zipcode='01190'),
            zipcode='01190', name='Ozan',  slug='ozan',  longitude=4.91667, latitude=46.3833,
        )
        self.assertTown(
            get_town(zipcode='01630'),
            zipcode='01630', name='Péron', slug='peron', longitude=5.93333, latitude=46.2,
        )
        self.assertTown(
            get_town(zipcode='97630'),
            zipcode='97630', name='Acoua', slug='acoua', longitude=45.0645, latitude=-12.7239,
        )
        self.assertTown(
            get_town(zipcode='17150'),
            zipcode='17150', name='Saint-Bonnet-sur-Gironde',
            slug='saint-bonnet-sur-gironde', longitude=-0.666667, latitude=45.35,
        )

    def test_populate_invalid_ignored(self):
        self.command.import_town_database(
            [self.HEADER, self.OZAN, self.PERON, self.INVALID, self.ACOUA],
            {'country': 'FRANCE'},
        )
        self.assertEqual(3, Town.objects.count())

        get_town = Town.objects.get
        self.assertTown(
            get_town(zipcode='01190'),
            zipcode='01190', name='Ozan',  slug='ozan',  longitude=4.91667, latitude=46.3833,
        )
        self.assertTown(
            get_town(zipcode='01630'),
            zipcode='01630', name='Péron', slug='peron', longitude=5.93333, latitude=46.2,
        )
        self.assertTown(
            get_town(zipcode='97630'),
            zipcode='97630', name='Acoua', slug='acoua', longitude=45.0645, latitude=-12.7239,
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_create_geoaddress_no_town(self):
        user = self.login_as_root_and_get()

        self.assertEqual(0, GeoAddress.objects.count())

        self.command.populate_addresses()
        self.assertEqual(0, GeoAddress.objects.count())

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = Address.objects.create(
            name='Addresse',
            address='27 bis rue du yahourt',
            po_box='',
            zipcode='13008',
            city='Marseille',
            department='13',
            state='',
            country='FRANCE',
            owner=orga,
        )

        GeoAddress.objects.all().delete()

        with self.assertRaises(GeoAddress.DoesNotExist):
            self.refresh(address).geoaddress

        self.command.populate_addresses()

        geo_address = self.get_alone_element(GeoAddress.objects.all())

        address = self.refresh(address)
        self.assertEqual(address.geoaddress, geo_address)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_create_geoaddress_with_town(self):
        user = self.login_as_root_and_get()
        self.command.import_town_database(
            [self.HEADER, self.OZAN, self.PERON, self.ACOUA, self.STBONNET],
            {'country': 'FRANCE'},
        )

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = Address.objects.create(
            name='Addresse',
            address='27 bis rue du yahourt',
            po_box='',
            zipcode='01630',
            city='Péron',
            department='01',
            state='',
            country='FRANCE',
            owner=orga,
        )

        GeoAddress.objects.all().delete()

        with self.assertRaises(GeoAddress.DoesNotExist):
            self.refresh(address).geoaddress

        self.command.populate_addresses()

        geo_address = self.get_alone_element(GeoAddress.objects.all())

        address = self.refresh(address)
        self.assertEqual(address.geoaddress, geo_address)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            longitude=5.93333, latitude=46.2,
            draggable=True, geocoded=False,
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_populate_empty(self):
        "No zipcode, no city."
        user = self.login_as_root_and_get()
        self.command.import_town_database(
            [self.HEADER, self.OZAN, self.PERON, self.ACOUA, self.STBONNET],
            {'country': 'FRANCE'},
        )

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = Address.objects.create(
            name='My address',
            address='27 bis rue du yahourt',
            po_box='',
            zipcode='',
            city='',
            department='01',
            state='',
            country='FRANCE',
            owner=orga,
        )

        GeoAddress.objects.all().delete()

        with self.assertRaises(GeoAddress.DoesNotExist):
            self.refresh(address).geoaddress

        self.command.populate_addresses()

        with self.assertRaises(GeoAddress.DoesNotExist):
            self.refresh(address).geoaddress
