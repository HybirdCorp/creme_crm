# -*- coding: utf-8 -*-

from os.path import join

from django.conf import settings
from django.test.utils import override_settings

from ..fetchers.filesystem import FileSystemFetcher
from .base import CrudityTestCase


class FetcherFileSystemTestCase(CrudityTestCase):
    @override_settings(CRUDITY_FILESYS_FETCHER_DIR='')
    def test_error01(self):
        self.assertEqual([], FileSystemFetcher().fetch())

    @override_settings(
        CRUDITY_FILESYS_FETCHER_DIR=join(
            settings.CREME_ROOT, 'static', 'chantilly', 'images', 'INVALID.xcf',
        ),
    )
    def test_error02(self):
        self.assertListEqual([], FileSystemFetcher().fetch())

    @override_settings(
        CRUDITY_FILESYS_FETCHER_DIR=join(
            settings.CREME_ROOT, 'static', 'chantilly', 'images', 'add_16.png',
        )
    )
    def test_error03(self):
        self.assertListEqual([], FileSystemFetcher().fetch())

    @override_settings(
        CRUDITY_FILESYS_FETCHER_DIR=join(settings.CREME_ROOT, 'static', 'common', 'fonts')
    )
    def test_ok01(self):
        paths = FileSystemFetcher().fetch()
        self.assertIsList(paths)
        self.assertIn(join(settings.CRUDITY_FILESYS_FETCHER_DIR, 'LICENSE.txt'), paths)

    @override_settings(
        MY_FILESYS_FETCHER_DIR=join(settings.CREME_ROOT, 'static', 'common', 'fonts')
    )
    def test_ok02(self):
        "Setting passed to the constructor."
        paths = FileSystemFetcher(setting_name='MY_FILESYS_FETCHER_DIR').fetch()
        self.assertIsList(paths)
        self.assertIn(join(settings.MY_FILESYS_FETCHER_DIR, 'LICENSE.txt'), paths)
