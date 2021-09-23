# from os.path import join
# from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
# from django.utils.translation import gettext as _
from django.test.utils import override_settings

from ..fetchers import CrudityFetcherManager
# from ..fetchers.filesystem import FileSystemFetcher
from ..fetchers.filesystem import NEWFileSystemFetcher
from ..fetchers.pop import NEWPopFetcher
from .base import CrudityTestCase


# TODO: CrudityTestCase useful?
class FetcherManagerTestCase(CrudityTestCase):
    def test_empty(self):
        "Empty."
        mngr = CrudityFetcherManager([])
        self.assertFalse([*mngr.fetcher_classes])
        self.assertIsNone(mngr.fetcher(
            fetcher_id=NEWFileSystemFetcher.id,
            fetcher_data={'path': '/home/creme/crud_import/ini/'},
        ))

    def test_direct_settings(self):
        "Settings passed directly."
        file_path1 = '/home/creme/crud_import/ini/'  # ######
        mngr = CrudityFetcherManager([
            'creme.crudity.fetchers.filesystem.NEWFileSystemFetcher',
            'creme.crudity.fetchers.pop.NEWPopFetcher',
        ])
        self.assertCountEqual(
            [NEWFileSystemFetcher, NEWPopFetcher],
            [*mngr.fetcher_classes],
        )

        fs_data = {'path': file_path1}
        fetcher1 = mngr.fetcher(
            fetcher_id=NEWFileSystemFetcher.id,
            fetcher_data=fs_data,
        )
        self.assertIsInstance(fetcher1, NEWFileSystemFetcher)
        self.assertDictEqual(fs_data, fetcher1.options)

        pop_data = {
            'url': 'pop.cremecrm.org',
            'username': 'creme_crudity',
            'password': '123456',
            'port': 110,
            # TODO: 'use_ssl'....
        }
        fetcher2 = mngr.fetcher(
            fetcher_id=NEWPopFetcher.id,
            fetcher_data=pop_data,
        )
        self.assertIsInstance(fetcher2, NEWPopFetcher)
        self.assertIsInstance(fetcher2.options, dict)
        self.assertDictEqual(pop_data, fetcher2.options)

    @override_settings(CRUDITY_FETCHERS=[
        'creme.crudity.fetchers.filesystem.NEWFileSystemFetcher',
    ])
    def test_default_settings(self):
        mngr = CrudityFetcherManager()
        self.assertListEqual([NEWFileSystemFetcher], [*mngr.fetcher_classes])

    def test_errors01(self):
        "Invalid path."
        mngr = CrudityFetcherManager([
            'creme.crudity.fetchers.doesnotexist.UnknownFetcher',
        ])

        with self.assertRaises(ImproperlyConfigured) as cm1:
            _ = [*mngr.fetcher_classes]

        msg = (
            '"creme.crudity.fetchers.doesnotexist.UnknownFetcher" is an invalid '
            'path of <CrudityFetcher> (see CRUDITY_FETCHERS).'
        )
        self.assertEqual(msg, str(cm1.exception))

        # ---
        with self.assertRaises(ImproperlyConfigured) as cm2:
            _ = mngr.fetcher(
                fetcher_id=NEWFileSystemFetcher.id,
                fetcher_data={'path': '/home/creme/crudity/'},
            )
        self.assertEqual(msg, str(cm2.exception))

    def test_errors02(self):
        "Invalid class."
        mngr = CrudityFetcherManager(['creme.crudity.models.WaitingAction'])

        with self.assertRaises(ImproperlyConfigured) as cm1:
            _ = [*mngr.fetcher_classes]

        msg = (
            '"creme.crudity.models.WaitingAction" is not a <CrudityFetcher> '
            'sub-class (see CRUDITY_FETCHERS).'
        )
        self.assertEqual(msg, str(cm1.exception))

        # ---
        with self.assertRaises(ImproperlyConfigured) as cm2:
            _ = mngr.fetcher(
                fetcher_id=NEWFileSystemFetcher.id,
                fetcher_data={'path': '/home/creme/crudity/'},
            )

        self.assertEqual(msg, str(cm2.exception))


# class FetcherFileSystemTestCase(CrudityTestCase):
#     @override_settings(CRUDITY_FILESYS_FETCHER_DIR='')
#     def test_error01(self):
#         self.assertEqual([], FileSystemFetcher().fetch())
#
#     @override_settings(
#         CRUDITY_FILESYS_FETCHER_DIR=join(
#             settings.CREME_ROOT, 'static', 'chantilly', 'images', 'INVALID.xcf',
#         ),
#     )
#     def test_error02(self):
#         self.assertListEqual([], FileSystemFetcher().fetch())
#
#     @override_settings(
#         CRUDITY_FILESYS_FETCHER_DIR=join(
#             settings.CREME_ROOT, 'static', 'chantilly', 'images', 'add_16.png',
#         )
#     )
#     def test_error03(self):
#         self.assertListEqual([], FileSystemFetcher().fetch())
#
#     @override_settings(
#         CRUDITY_FILESYS_FETCHER_DIR=join(settings.CREME_ROOT, 'static', 'common', 'fonts')
#     )
#     def test_ok01(self):
#         paths = FileSystemFetcher().fetch()
#         self.assertIsList(paths)
#         self.assertIn(join(settings.CRUDITY_FILESYS_FETCHER_DIR, 'LICENSE.txt'), paths)
#
#     @override_settings(
#         MY_FILESYS_FETCHER_DIR=join(settings.CREME_ROOT, 'static', 'common', 'fonts')
#     )
#     def test_ok02(self):
#         "Setting passed to the constructor."
#         paths = FileSystemFetcher(setting_name='MY_FILESYS_FETCHER_DIR').fetch()
#         self.assertIsList(paths)
#         self.assertIn(join(settings.MY_FILESYS_FETCHER_DIR, 'LICENSE.txt'), paths)
