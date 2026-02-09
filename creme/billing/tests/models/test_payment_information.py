from functools import partial
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.billing.models import PaymentInformation
from creme.creme_core.core.exceptions import SpecificProtectedError
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import Organisation, _BillingTestCase


@skipIfCustomOrganisation
class PaymentInformationTestCase(_BillingTestCase):
    def test_create(self):
        user = self.get_root_user()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        name = 'RIB #1'
        bank_code = 'B999'
        counter_code = '123789-BC'
        account_number = '0000'
        rib_key = '42'
        domiciliation = 'Fantasia'
        iban = 'IBAN'
        bic = 'BIC'
        pi1 = PaymentInformation.objects.create(
            organisation=organisation,
            name=name, bank_code=bank_code, counter_code=counter_code,
            account_number=account_number, rib_key=rib_key,
            banking_domiciliation=domiciliation, iban=iban, bic=bic,
        )
        self.assertIsInstance(pi1.uuid, UUID)
        self.assertEqual(name,           pi1.name)
        self.assertEqual(bank_code,      pi1.bank_code)
        self.assertEqual(counter_code,   pi1.counter_code)
        self.assertEqual(account_number, pi1.account_number)
        self.assertEqual(rib_key,        pi1.rib_key)
        self.assertEqual(domiciliation,  pi1.banking_domiciliation)
        self.assertEqual(iban,           pi1.iban)
        self.assertEqual(bic,            pi1.bic)
        self.assertTrue(pi1.is_default)
        self.assertIsNone(pi1.archived)

        # ---
        pi2 = PaymentInformation.objects.create(
            organisation=organisation, name='RIB #2', is_default=True,
        )
        self.assertEqual('', pi2.bank_code)
        self.assertEqual('', pi2.counter_code)
        self.assertEqual('', pi2.account_number)
        self.assertEqual('', pi2.rib_key)
        self.assertEqual('', pi2.banking_domiciliation)
        self.assertEqual('', pi2.iban)
        self.assertEqual('', pi2.bic)
        self.assertTrue(pi2.is_default)

        self.assertFalse(self.refresh(pi1).is_default)

    def test_delete__one_instance(self):
        user = self.get_root_user()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Nintendo')
        orga2 = create_orga(name='Sega')

        create_pi = PaymentInformation.objects.create
        pi_11 = create_pi(organisation=orga1, name='RIB 1')
        pi_21 = create_pi(organisation=orga2, name='RIB 1')
        pi_22 = create_pi(organisation=orga2, name='RIB 2', is_default=True)

        pi_11.delete()  # TODO: exception (because only one)?
        self.assertDoesNotExist(pi_11)
        self.assertFalse(self.refresh(pi_21).is_default)
        self.assertTrue(self.refresh(pi_22).is_default)

    def test_delete__two_instances__not_default(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Nintendo')

        create_pi = PaymentInformation.objects.create
        pi1 = create_pi(organisation=orga, name='RIB 1', is_default=True)
        pi2 = create_pi(organisation=orga, name='RIB 2', is_default=False)

        pi2.delete()
        self.assertDoesNotExist(pi2)
        self.assertIs(True, self.refresh(pi1).is_default)

    def test_delete__two_instances__default(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Nintendo')

        create_pi = PaymentInformation.objects.create
        pi1 = create_pi(organisation=orga, name='RIB 1', is_default=True)
        pi2 = create_pi(organisation=orga, name='RIB 2', is_default=False)

        pi1.delete()
        self.assertDoesNotExist(pi1)
        self.assertTrue(self.refresh(pi2).is_default)

    def test_delete__two_instances__archived(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(user=user, name='Nintendo')

        create_pi = PaymentInformation.objects.create
        create_pi(organisation=orga, name='RIB 1', is_default=True)
        pi2 = create_pi(organisation=orga, name='RIB 2', archived=now())

        pi2.delete()
        self.assertDoesNotExist(pi2)

    def test_delete__two_instances__archived__error(self):
        "Deletion is not possible if the remaining accounts are archived."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Nintendo')
        orga2 = create_orga(name='Sega')

        create_pi = PaymentInformation.objects.create
        pi1 = create_pi(organisation=orga1, name='RIB 1', is_default=True)
        create_pi(organisation=orga1, name='RIB 2', archived=now())
        create_pi(organisation=orga2, name='RIB orga 2')  # Should be excluded

        with self.assertRaises(SpecificProtectedError) as cm:
            pi1.delete()
        msg = _('You cannot delete this account because all other accounts are archived')
        self.assertEqual(msg, str(cm.exception.args[0]))

        # With view ---
        ct = ContentType.objects.get_for_model(PaymentInformation)

        response = self.client.post(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': pi1.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertContains(response=response, status_code=409, text=msg)

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
