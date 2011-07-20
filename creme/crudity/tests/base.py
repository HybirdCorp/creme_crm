# -*- coding: utf-8 -*-

from creme_core.tests.base import CremeTestCase
from creme_core.models.entity import CremeEntity

from creme_config.models.setting import SettingValue
from crudity.backends.email.create.base import CreateFromEmailBackend

from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER


class CrudityTestCase(CremeTestCase):
    def setUp(self):
        self.login()
        self.populate('crudity',)

    def _set_sandbox_by_user(self):
        sv = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = "True"
        sv.save()

    def _get_create_from_email_backend(self, password="", in_sandbox=True, subject="", model=CremeEntity, body_map={}, limit_froms=(), backend_klass=CreateFromEmailBackend):
        backend = backend_klass()
        backend.password = password
        backend.in_sandbox = in_sandbox
        backend.subject = subject
        backend.model = model
        backend.body_map = body_map
        backend.limit_froms = limit_froms
        return backend
