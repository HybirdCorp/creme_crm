# -*- coding: utf-8 -*-

from creme.creme_core.backends import _BackendRegistry, base
from creme.creme_core.backends.csv_import import CSVImportBackend
from creme.creme_core.backends.xls_import import XLSImportBackend

from .base import CremeTestCase


class BackendsTestCase(CremeTestCase):
    def test_registry(self):
        registry = _BackendRegistry(base.ImportBackend, [
            'creme.creme_core.backends.csv_import.CSVImportBackend',
            'creme.creme_core.backends.xls_import.XLSImportBackend',
        ])

        # self.assertEqual(CSVImportBackend, registry.get_backend(CSVImportBackend.id))
        # self.assertEqual(XLSImportBackend, registry.get_backend(XLSImportBackend.id))
        self.assertEqual(CSVImportBackend, registry.get_backend_class(CSVImportBackend.id))
        self.assertEqual(XLSImportBackend, registry.get_backend_class(XLSImportBackend.id))
        # self.assertIsNone(registry.get_backend('unknown'))
        # self.assertSetEqual(
        #     {CSVImportBackend, XLSImportBackend}, {*registry.backends}
        # )
        self.assertSetEqual(
            {CSVImportBackend, XLSImportBackend}, {*registry.backend_classes}
        )
        self.assertSetEqual(
            {CSVImportBackend.id, XLSImportBackend.id}, {*registry.extensions}
        )

    def test_registration_errors01(self):
        "Duplicates."
        registry = _BackendRegistry(base.ImportBackend, [
            'creme.creme_core.backends.csv_import.CSVImportBackend',
            'creme.creme_core.backends.csv_import.CSVImportBackend',  # Twice
        ])

        # with self.assertRaises(registry.DuplicatedId):
        #     registry.get_backend(CSVImportBackend.id)

        with self.assertRaises(registry.DuplicatedId):
            registry.get_backend_class(CSVImportBackend.id)

    def test_registration_errors02(self):
        "Invalid path."
        path = 'creme.creme_core.backends.csv_import.Unknown'
        registry = _BackendRegistry(base.ImportBackend, [path])

        with self.assertLogs(level='WARNING') as log_cm:
            backend = registry.get_backend_class(CSVImportBackend.id)

        self.assertIsNone(backend)

        messages = log_cm.output
        self.assertEqual(1, len(messages))
        self.assertStartsWith(
            messages[0],
            f'WARNING:creme.creme_core.utils.imports:'
            f'An error occurred trying to import "{path}":'
        )

    def test_registration_errors03(self):
        "Invalid class."
        registry = _BackendRegistry(base.ExportBackend, [
            'creme.creme_core.backends.csv_import.CSVImportBackend',
        ])

        with self.assertRaises(registry.InvalidClass):
            registry.get_backend_class(CSVImportBackend.id)
