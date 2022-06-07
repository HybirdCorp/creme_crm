from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_api.api.contenttypes.utils import get_cremeentity_contenttypes
from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons import get_contact_model

Contact = get_contact_model()


class RetrieveContentTypeTestCase(CremeAPITestCase):
    url_name = "creme_api__contenttypes-detail"
    method = "get"

    def test_retrieve_contenttype(self):
        contact_ct = ContentType.objects.get_for_model(Contact)

        response = self.make_request(to=contact_ct.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": contact_ct.id,
                "application": _("Accounts and Contacts"),
                "name": _("Contacts"),
            },
        )


class ListContentTypeTestCase(CremeAPITestCase):
    url_name = "creme_api__contenttypes-list"
    method = "get"

    def test_list_contenttypes(self):
        responses, data = self.consume_list()
        self.assertEqual(len(data), len(get_cremeentity_contenttypes()))
