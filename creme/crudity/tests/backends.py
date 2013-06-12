# -*- coding: utf-8 -*-

try:
    from creme.creme_config.models import SettingValue

    from creme.persons.models import Contact

    from ..backends.models import CrudityBackend
    from ..constants import SETTING_CRUDITY_SANDBOX_BY_USER
    from ..exceptions import ImproperlyConfiguredBackend
    from ..registry import crudity_registry
    from .base import CrudityTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class BackendsTestCase(CrudityTestCase):
    def _get_backend(self, model_klass, password=u"", in_sandbox=True,
                     body_map=None, subject=u"", limit_froms=()):
        class SubCrudityBackend(CrudityBackend):
            model = model_klass

        return SubCrudityBackend({'password':    password,
                                  'in_sandbox':  in_sandbox,
                                  'subject':     subject,
                                  'limit_froms': limit_froms,
                                  'body_map':    body_map or {},
                                 }
                                )

    def test_is_configured01(self):
        backend = self._get_backend(Contact)
        self.assertFalse(backend.is_configured)

        backend2 = self._get_backend(Contact, subject="contact", body_map={'user_id': 1})
        self.assertTrue(backend2.is_configured)

    def test_check_configuration01(self):
        self.assertRaises(ImproperlyConfiguredBackend, self._get_backend,
                          Contact, subject="contact",
                          body_map={'user_id': 1, 'di_resu': 1}
                         )

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
            self.assertTrue(backend.is_sandbox_by_user)

        sv = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = "False"
        sv.save()

        for backend in backends:
            self.assertFalse(backend.is_sandbox_by_user)
