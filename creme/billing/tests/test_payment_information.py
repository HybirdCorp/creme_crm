# -*- coding: utf-8 -*-

from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FieldsConfig, SetCredentials
from creme.persons.tests.base import skipIfCustomOrganisation

from ..models import PaymentInformation
from .base import Invoice, Organisation, _BillingTestCase, skipIfCustomInvoice


@skipIfCustomOrganisation
class PaymentInformationTestCase(_BillingTestCase):
    @staticmethod
    def _build_add_url(orga):
        return reverse('billing__create_payment_info', args=(orga.id,))

    @staticmethod
    def _build_add_related_url(invoice):
        return reverse('billing__create_related_payment_info', args=(invoice.id,))

    @staticmethod
    def _build_setdefault_url(pi, invoice):
        return reverse('billing__set_default_payment_info', args=(pi.id, invoice.id))

    def test_createview01(self):
        user = self.login()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        url = self._build_add_url(organisation)

        context = self.assertGET200(url).context
        self.assertEqual(
            _(
                'New payment information in the organisation «{entity}»'
            ).format(entity=organisation),
            context.get('title')
        )
        self.assertEqual(_('Save the payment information'), context.get('submit_label'))

        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': f'RIB of {organisation}',
            },
        ))

        all_pi = PaymentInformation.objects.all()
        self.assertEqual(1, len(all_pi))

        pi = all_pi[0]
        self.assertIs(True, pi.is_default)
        self.assertEqual(organisation, pi.organisation)
        self.assertEqual('', pi.bank_code)
        self.assertEqual('', pi.counter_code)
        self.assertEqual('', pi.account_number)
        self.assertEqual('', pi.rib_key)
        self.assertEqual('', pi.banking_domiciliation)
        self.assertEqual('', pi.iban)
        self.assertEqual('', pi.bic)

    def test_createview02(self):
        user = self.login()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        first_pi = PaymentInformation.objects.create(
            organisation=organisation, name='RIB 1', is_default=True,
        )

        url = self._build_add_url(organisation)
        self.assertGET200(url)

        bank_code = 'BANK'
        counter_code = 'COUNTER'
        account_number = 'ACCOUNT'
        key = '12345'
        domiciliation = 'DOM'
        iban = 'IBAN'
        bic = 'BIC'
        response = self.client.post(
            url,
            data={
                'user':       user.pk,
                'name':       f'RIB of {organisation}',
                'is_default': True,

                'bank_code':             bank_code,
                'counter_code':          counter_code,
                'account_number':        account_number,
                'rib_key':               key,
                'banking_domiciliation': domiciliation,
                'iban':                  iban,
                'bic':                   bic,
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(2, PaymentInformation.objects.count())

        second_pi = PaymentInformation.objects.exclude(pk=first_pi.pk)[0]
        self.assertIs(True, second_pi.is_default)

        second_pi.delete()
        self.assertIs(True, first_pi.is_default)
        self.assertEqual(bank_code,      second_pi.bank_code)
        self.assertEqual(counter_code,   second_pi.counter_code)
        self.assertEqual(account_number, second_pi.account_number)
        self.assertEqual(key,            second_pi.rib_key)
        self.assertEqual(domiciliation,  second_pi.banking_domiciliation)
        self.assertEqual(iban,           second_pi.iban)
        self.assertEqual(bic,            second_pi.bic)

    def test_createview03(self):
        "Related is not an organisation."
        user = self.login()
        self.assertGET404(self._build_add_url(user.linked_contact))

    def test_related_createview01(self):
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Organisation, Invoice],
        )

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role, set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            ctype=Invoice,
        )
        create_sc(
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            ctype=Organisation,
        )

        invoice, source, target = self.create_invoice_n_orgas('Playstations')
        url = self._build_add_related_url(invoice)

        context = self.assertGET200(url).context
        self.assertEqual(
            _(
                'New payment information in the organisation «{entity}»'
            ).format(entity=source),
            context.get('title')
        )
        self.assertEqual(_('Save the payment information'), context.get('submit_label'))

        self.assertNoFormError(self.client.post(
            url,
            data={
                'user': user.pk,
                'name': f'RIB of {source}',
            },
        ))

        all_pi = PaymentInformation.objects.filter(organisation=source.id)
        self.assertEqual(1, len(all_pi))

        pi = all_pi[0]
        self.assertIs(True, pi.is_default)
        self.assertEqual(pi, self.refresh(invoice).payment_info)

        # Not a billing doc
        self.assertGET404(self._build_add_related_url(source))

    def test_related_createview02(self):
        "Credentials for source."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Organisation, Invoice],
        )

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role, set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE,
            ctype=Invoice,
        )
        create_sc(
            value=EntityCredentials.VIEW | EntityCredentials.LINK,  # No CHANGE
            ctype=Organisation,
        )

        invoice, source, target = self.create_invoice_n_orgas('Playstations')
        self.assertGET403(self._build_add_related_url(invoice))

    def test_editview01(self):
        user = self.login()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        pi = PaymentInformation.objects.create(organisation=organisation, name='RIB 1')

        url = pi.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Payment information for «{entity}»').format(entity=organisation),
            response.context.get('title')
        )

        rib_key = '00'
        name = f'RIB of {organisation}'
        bic = 'pen ?'
        response = self.client.post(
            url,
            data={
                'user':    user.pk,
                'name':    name,
                'rib_key': rib_key,
                'bic':     bic,
            },
        )
        self.assertNoFormError(response)

        pi = self.refresh(pi)
        self.assertIs(True, pi.is_default)
        self.assertEqual(name,    pi.name)
        self.assertEqual(rib_key, pi.rib_key)
        self.assertEqual(bic,     pi.bic)

    def test_editview02(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='Nintendo')
        orga2 = create_orga(name='Sega')

        create_pi = PaymentInformation.objects.create
        # First if no filter by organisation
        create_pi(organisation=orga2, name='RIB 1', is_default=True)

        pi_11 = create_pi(organisation=orga1, name='RIB 1', is_default=True)
        pi_12 = create_pi(organisation=orga1, name='RIB 2', is_default=False)

        self.assertTrue(self.refresh(pi_11).is_default)

        url = pi_12.get_edit_absolute_url()
        self.assertGET200(url)

        rib_key = '00'
        name = f'RIB of {orga1}'
        bic = 'pen ?'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user':       user.pk,
                'name':       name,
                'rib_key':    rib_key,
                'bic':        bic,
                'is_default': True,
            },
        ))

        pi_11 = self.refresh(pi_11)
        pi_12 = self.refresh(pi_12)

        self.assertFalse(pi_11.is_default)
        self.assertTrue(pi_12.is_default)

        self.assertEqual(name,    pi_12.name)
        self.assertEqual(rib_key, pi_12.rib_key)
        self.assertEqual(bic,     pi_12.bic)

        pi_12.delete()
        self.assertIs(True, self.refresh(pi_11).is_default)

    @skipIfCustomInvoice
    def test_set_default_in_invoice01(self):
        self.login()

        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name='RIB sony')
        url = self._build_setdefault_url(pi_sony, invoice)
        self.assertGET405(url)
        self.assertPOST200(url)
        self.assertEqual(pi_sony, self.refresh(invoice).payment_info)

    @skipIfCustomInvoice
    def test_set_default_in_invoice02(self):
        user = self.login()

        sega = Organisation.objects.create(user=user, name='Sega')
        invoice, sony_source, nintendo_target = self.create_invoice_n_orgas('Playstations')

        create_pi = PaymentInformation.objects.create
        pi_nintendo = create_pi(organisation=nintendo_target, name='RIB nintendo')
        pi_sony     = create_pi(organisation=sony_source,     name='RIB sony')
        pi_sega     = create_pi(organisation=sega,            name='RIB sega')

        def assertPostStatus(code, pi):
            self.assertEqual(
                code,
                self.client.post(self._build_setdefault_url(pi, invoice)).status_code
            )

        assertPostStatus(409, pi_nintendo)
        assertPostStatus(409, pi_sega)
        assertPostStatus(200, pi_sony)

    @skipIfCustomInvoice
    def test_set_default_in_invoice03(self):
        "Trashed organisation."
        self.login()

        invoice, sony_source = self.create_invoice_n_orgas('Playstations')[:2]
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name='RIB sony')

        sony_source.trash()

        self.assertPOST403(self._build_setdefault_url(pi_sony, invoice))
        self.assertNotEqual(pi_sony, self.refresh(invoice).payment_info)

    @skipIfCustomInvoice
    def test_set_default_in_invoice04(self):
        "'payment_info' is hidden."
        self.login()

        invoice, sony_source = self.create_invoice_n_orgas('Playstations')[:2]
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name='RIB sony')

        FieldsConfig.objects.create(
            content_type=Invoice,
            descriptions=[('payment_info', {FieldsConfig.HIDDEN: True})],
        )

        self.assertPOST409(self._build_setdefault_url(pi_sony, invoice))

    def test_inneredit(self):
        user = self.login()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        pi = PaymentInformation.objects.create(organisation=organisation, name='RIB 1')

        build_url = self.build_inneredit_url
        url = build_url(pi, 'name')
        self.assertGET200(url)

        name = pi.name + ' (default)'
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(pi)],
                'field_value':  name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(pi).name)

        self.assertGET(400, build_url(pi, 'organisation'))
