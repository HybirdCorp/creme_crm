# -*- coding: utf-8 -*-
from creme_config.models.setting import SettingValue

from crudity.backends.models import CrudityBackend
from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from crudity.exceptions import ImproperlyConfiguredBackend
from crudity.registry import crudity_registry, CRUDityRegistry
from crudity.tests.base import CrudityTestCase
from persons.models.contact import Contact

class BackendsTestCase(CrudityTestCase):
    def _get_backend(self, model_klass, password=u"", in_sandbox=True, body_map={}, subject=u"", limit_froms=()):
        class SubCrudityBackend(CrudityBackend):
            model = model_klass

        return SubCrudityBackend({'password': password, 'in_sandbox': in_sandbox, 'subject': subject, 'limit_froms': limit_froms, 'body_map': body_map})

    def test_is_configured01(self):
        backend = self._get_backend(Contact)
        self.assertFalse(backend.is_configured)

        backend2 = self._get_backend(Contact, subject="contact", body_map={'user_id': 1})
        self.assert_(backend2.is_configured)

    def test_check_configuration01(self):
        self.assertRaises(ImproperlyConfiguredBackend, self._get_backend, Contact, subject="contact", body_map={'user_id': 1, 'di_resu': 1})

    def test_is_sandbox_by_user_property01(self):
        self._set_sandbox_by_user()

        fetchers = crudity_registry.get_fetchers()
        inputs = []
        for fetcher in fetchers:
            for inputs_dict in fetcher.get_inputs():
                inputs.extend(inputs_dict.values())

        backends = []
        for input in inputs:
            backends.extend(input.get_backends())

        for backend in backends:
            self.assert_(backend.is_sandbox_by_user)

        sv = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = "False"
        sv.save()

        for backend in backends:
            self.assertFalse(backend.is_sandbox_by_user)
