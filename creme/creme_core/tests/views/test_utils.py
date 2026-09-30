from django.urls import reverse

from creme.creme_core.tests.fake_views import ToBeDisabled
from creme.creme_core.views.utils import disable_view

from ..base import CremeTestCase


class UtilsTestCase(CremeTestCase):
    def test_disable_view(self):
        self.login_as_root()

        url = reverse('creme_core__fake_view_to_be_disabled', args=(1,))
        self.assertGET200(url)
        self.assertPOST200(url)

        msg = 'These view has been disabled in tests'
        disable_view(ToBeDisabled, message=msg)
        self.assertContains(self.client.get(url), text=msg, status_code=409)
        self.assertContains(self.client.post(url), text=msg, status_code=409)
        self.assertEqual(405, self.client.put(url).status_code)
