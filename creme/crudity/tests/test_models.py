from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings

from creme.creme_core.tests.fake_models import FakeContact

from ..core import RegularFieldExtractor
from ..fetchers.filesystem import NEWFileSystemFetcher
from ..fetchers.pop import NEWPopFetcher
from ..models import FetcherConfigItem, MachineConfigItem
from .base import CrudityTestCase


class FetcherConfigItemTestCase(CrudityTestCase):
    def test_no_class(self):
        item = FetcherConfigItem(class_id='')
        self.assertIsNone(item.fetcher)

    @override_settings(CRUDITY_FETCHERS=[
        'creme.crudity.fetchers.filesystem.NEWFileSystemFetcher',
    ])
    def test_invalid_class(self):
        self.assertIsNone(FetcherConfigItem(class_id='invalid').fetcher)
        self.assertIsNone(FetcherConfigItem(class_id='crudity-pop').fetcher)

    @override_settings(CRUDITY_FETCHERS=[
        'creme.crudity.fetchers.invalid.InvalidFetcher',  # Does not exist
    ])
    def test_bad_config01(self):
        with self.assertRaises(ImproperlyConfigured) as cm:
            _ = FetcherConfigItem(class_id='crudity-pop').fetcher

        self.assertEqual(
            '"creme.crudity.fetchers.invalid.InvalidFetcher" is an invalid path '
            'of <CrudityFetcher> (see CRUDITY_FETCHERS).',
            str(cm.exception),
        )

    @override_settings(CRUDITY_FETCHERS=[
        'creme.crudity.decoders.ini.IniDecoder',  # Not a fetcher
    ])
    def test_bad_config02(self):
        with self.assertRaises(ImproperlyConfigured) as cm:
            _ = FetcherConfigItem(class_id='crudity-pop').fetcher

        self.assertEqual(
            '"creme.crudity.decoders.ini.IniDecoder" is not a <CrudityFetcher> '
            'sub-class (see CRUDITY_FETCHERS).',
            str(cm.exception),
        )

    @override_settings(CRUDITY_FETCHERS=[
        'creme.crudity.fetchers.pop.NEWPopFetcher',
    ])
    def test_pop(self):
        options = {
            'url': 'pop.cremecrm.org',
            'username': 'creme_crudity',
            'password': '123456',
            'port': 110,
            # TODO: 'use_ssl'....
        }
        item = FetcherConfigItem.objects.create(class_id='crudity-pop', options=options)

        fetcher = self.refresh(item).fetcher
        self.assertIsInstance(fetcher, NEWPopFetcher)
        self.assertDictEqual(options, fetcher.options)

    @override_settings(CRUDITY_FETCHERS=[
        'creme.crudity.fetchers.pop.NEWPopFetcher',
        'creme.crudity.fetchers.filesystem.NEWFileSystemFetcher',
    ])
    def test_filesystem(self):
        options = {'path': '/home/creme/crud_import/ini/'}
        item = FetcherConfigItem.objects.create(
            class_id='crudity-filesystem',
            options=options
        )

        fetcher = self.refresh(item).fetcher
        self.assertIsInstance(fetcher, NEWFileSystemFetcher)
        self.assertDictEqual(options, fetcher.options)


class MachinesConfigItemTestCase(CrudityTestCase):
    def test_extractors01(self):
        fetcher_item = FetcherConfigItem.objects.create(
            class_id='crudity-filesystem',
            options={'path': '/home/creme/crud_import/ini/'},
        )
        item = MachineConfigItem(
            action_type=MachineConfigItem.CRUDAction.CREATE,
            content_type=FakeContact,
            fetcher_item=fetcher_item,
            # json_extractors=[],
        )
        self.assertListEqual([], item.extractors)

    def test_extractors02(self):
        fetcher_item = FetcherConfigItem.objects.create(
            class_id='crudity-filesystem',
            options={'path': '/home/creme/crud_import/ini/'},
        )
        item = MachineConfigItem.objects.create(
            action_type=MachineConfigItem.CRUDAction.CREATE,
            content_type=FakeContact,
            fetcher_item=fetcher_item,
            extractors=[
                RegularFieldExtractor(model=FakeContact, value='last_name'),
                RegularFieldExtractor(model=FakeContact, value='first_name'),
            ],
        )
        self.assertListEqual(
            [
                RegularFieldExtractor(model=FakeContact, value='last_name'),
                RegularFieldExtractor(model=FakeContact, value='first_name'),
            ],
            self.refresh(item).extractors,
        )
