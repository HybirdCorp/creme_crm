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

        self.assertEqual(CSVImportBackend, registry.get_backend_class(CSVImportBackend.id))
        self.assertEqual(XLSImportBackend, registry.get_backend_class(XLSImportBackend.id))
        self.assertCountEqual(
            [CSVImportBackend, XLSImportBackend], registry.backend_classes,
        )
        self.assertCountEqual(
            [CSVImportBackend.id, XLSImportBackend.id], registry.extensions,
        )
        self.assertTrue(registry)

    def test_registry__empty(self):
        registry = _BackendRegistry(base.ImportBackend, [])
        self.assertFalse([*registry.backend_classes])
        self.assertFalse([*registry.extensions])
        self.assertFalse(registry)

    def test_registration_errors01(self):
        "Duplicates."
        registry = _BackendRegistry(base.ImportBackend, [
            'creme.creme_core.backends.csv_import.CSVImportBackend',
            'creme.creme_core.backends.csv_import.CSVImportBackend',  # Twice
        ])

        with self.assertRaises(registry.DuplicatedId):
            registry.get_backend_class(CSVImportBackend.id)

    def test_registration_errors02(self):
        "Invalid path."
        path = 'creme.creme_core.backends.csv_import.Unknown'
        registry = _BackendRegistry(base.ImportBackend, [path])

        with self.assertLogs(level='WARNING') as log_cm:
            backend = registry.get_backend_class(CSVImportBackend.id)

        self.assertIsNone(backend)

        message = self.get_alone_element(log_cm.output)
        self.assertStartsWith(
            message,
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
