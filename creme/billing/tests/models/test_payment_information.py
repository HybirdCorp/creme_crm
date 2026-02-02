from creme.billing.models import PaymentInformation
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import Organisation, _BillingTestCase


@skipIfCustomOrganisation
class PaymentInformationTestCase(_BillingTestCase):
    def test_portable_key(self):
        user = self.get_root_user()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        pi = PaymentInformation.objects.create(organisation=organisation, name='RIB 1')

        with self.assertNoException():
            key = pi.portable_key()
        self.assertIsInstance(key, str)
        self.assertUUIDEqual(pi.uuid, key)

        # ---
        with self.assertNoException():
            got_pi = PaymentInformation.objects.get_by_portable_key(key)
        self.assertEqual(pi, got_pi)
