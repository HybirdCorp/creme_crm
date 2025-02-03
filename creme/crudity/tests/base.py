from creme.creme_core.models import SettingValue
from creme.creme_core.tests.base import CremeTestCase
from creme.documents import get_document_model, get_folder_model
from creme.persons import get_contact_model, get_organisation_model

from ..backends.models import CrudityBackend
# from ..constants import SETTING_CRUDITY_SANDBOX_BY_USER
from ..fetchers.base import CrudityFetcher
from ..inputs.base import CrudityInput
from ..setting_keys import sandbox_key
from ..utils import is_sandbox_by_user
from .fake_crudity_register import (
    FakeContactBackend,
    SwallowFetcher,
    SwallowInput,
)

Document = get_document_model()
Folder = get_folder_model()

Contact = get_contact_model()
Organisation = get_organisation_model()


class FakeFetcher(CrudityFetcher):
    def fetch(self, *args, **kwargs):
        return []


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
        super().setUpClass()

        cls.FakeContactBackend = FakeContactBackend
        cls.SwallowInput = SwallowInput
        cls.SwallowFetcher = SwallowFetcher

    def setUp(self):
        super().setUp()

        self.FakeContactBackend.calls_args.clear()
        self.SwallowInput.force_not_handle = False

        SwallowFetcher.user_id = 0
        SwallowFetcher.last_name = ''

    def _set_sandbox_by_user(self):
        # sv = SettingValue.objects.get(key_id=SETTING_CRUDITY_SANDBOX_BY_USER)
        sv = SettingValue.objects.get(key_id=sandbox_key.id)
        sv.value = True
        sv.save()

        self.assertTrue(is_sandbox_by_user())
