# -*- coding: utf-8 -*-

from creme_config.models.setting import SettingValue

from creme_core.tests.base import CremeTestCase
from persons.models import Contact, Organisation

from documents.models import Document

from crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from crudity.backends.models import CrudityBackend
from crudity.fetchers.base import CrudityFetcher
from crudity.inputs.base import CrudityInput

class FakeFetcher(CrudityFetcher):
    pass


class FakeInput(CrudityInput):
    pass


class ContactFakeBackend(CrudityBackend):
    model = Contact


class OrganisationFakeBackend(CrudityBackend):
    model = Organisation


class DocumentFakeBackend(CrudityBackend):
    model = Document

class CrudityTestCase(CremeTestCase):
    def setUp(self):
        self.login()
        self.populate('creme_config', 'crudity',)

    def _set_sandbox_by_user(self):
        sv = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = "True"
        sv.save()
