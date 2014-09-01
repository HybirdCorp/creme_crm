# -*- coding: utf-8 -*-

from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.models import SettingValue

from creme.persons.models import Contact, Organisation

from creme.documents.models import Document

from creme.activities.models import Activity

from ..constants import SETTING_CRUDITY_SANDBOX_BY_USER
from ..backends.models import CrudityBackend
from ..fetchers.base import CrudityFetcher
from ..inputs.base import CrudityInput


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


class ActivityFakeBackend(CrudityBackend):
    model = Activity


class CrudityTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core', 'creme_config', 'crudity')
        cls.autodiscover()

    def setUp(self):
        self.login()

    def _set_sandbox_by_user(self):
        sv = SettingValue.objects.get(key_id=SETTING_CRUDITY_SANDBOX_BY_USER, user=None)
        sv.value = True
        sv.save()
