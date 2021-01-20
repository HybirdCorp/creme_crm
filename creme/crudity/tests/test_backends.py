# -*- coding: utf-8 -*-

from creme.creme_core.tests.fake_models import FakeContact

from .. import registry
from ..backends.models import CrudityBackend
from ..exceptions import ImproperlyConfiguredBackend
from .base import CrudityTestCase


# TODO: factorise with CrudityViewsTestCase
class BackendsTestCase(CrudityTestCase):
    _original_crudity_registry = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._original_crudity_registry = registry.crudity_registry

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        registry.crudity_registry = cls._original_crudity_registry

    def _get_backend(self, model_klass, password='', in_sandbox=True,
                     body_map=None, subject='', limit_froms=()):
        class SubCrudityBackend(CrudityBackend):
            model = model_klass

        return SubCrudityBackend({
            'password':    password,
            'in_sandbox':  in_sandbox,
            'subject':     subject,
            'limit_froms': limit_froms,
            'body_map':    body_map or {},
        })

    def test_is_configured01(self):
        backend = self._get_backend(FakeContact)
        self.assertFalse(backend.is_configured)

        backend2 = self._get_backend(FakeContact, subject='contact', body_map={'user_id': 1})
        self.assertTrue(backend2.is_configured)

    def test_check_configuration01(self):
        self.assertRaises(
            ImproperlyConfiguredBackend,
            self._get_backend,
            FakeContact, subject='contact',
            body_map={'user_id': 1, 'di_resu': 1},
        )
