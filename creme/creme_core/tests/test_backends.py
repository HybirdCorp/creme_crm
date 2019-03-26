# -*- coding: utf-8 -*-

try:
    from .base import CremeTestCase

    from creme.creme_core.backends import _BackendRegistry
    from creme.creme_core.backends.csv_import import CSVImportBackend
    from creme.creme_core.backends.xls_import import XLSImportBackend
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class BackendsTestCase(CremeTestCase):
    def test_registry(self):
        registry = _BackendRegistry([
            'creme.creme_core.backends.csv_import.CSVImportBackend',
            'creme.creme_core.backends.xls_import.XLSImportBackend',
        ])

        self.assertEqual(CSVImportBackend, registry.get_backend(CSVImportBackend.id))
        self.assertEqual(XLSImportBackend, registry.get_backend(XLSImportBackend.id))
        self.assertIsNone(registry.get_backend('unknown'))

        # self.assertEqual({CSVImportBackend, XLSImportBackend},
        #                  set(registry.iterbackends())
        #                 )
        self.assertEqual({CSVImportBackend, XLSImportBackend},
                         set(registry.backends)
                        )

        # self.assertEqual({CSVImportBackend.id, XLSImportBackend.id},
        #                  set(registry.iterkeys())
        #                 )
        self.assertEqual({CSVImportBackend.id, XLSImportBackend.id},
                         set(registry.extensions)
                        )

    def test_registration_errors(self):
        registry = _BackendRegistry([
            'creme.creme_core.backends.csv_import.CSVImportBackend',
            'creme.creme_core.backends.csv_import.CSVImportBackend',  # Twice
        ])

        with self.assertRaises(registry.DuplicatedId):
            registry.get_backend(CSVImportBackend.id)

    # TODO: test with invalid path
