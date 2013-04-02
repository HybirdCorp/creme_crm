# -*- coding: utf-8 -*-

from creme.creme_config.models.setting import SettingValue

from creme.creme_core.tests.base import CremeTestCase

from creme.persons.models import Contact, Organisation

from creme.documents.models import Document

from creme.crudity.constants import SETTING_CRUDITY_SANDBOX_BY_USER
from creme.crudity.backends.models import CrudityBackend
from creme.crudity.fetchers.base import CrudityFetcher
from creme.crudity.inputs.base import CrudityInput


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
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'crudity')

    def setUp(self):
        self.login()

    def _set_sandbox_by_user(self):
        sv = SettingValue.objects.get(key=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = "True"
        sv.save()
