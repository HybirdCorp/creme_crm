from functools import partial

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.billing.models import PaymentInformation
from creme.creme_core.models import FieldsConfig
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import Invoice, Organisation, _BillingTestCase, skipIfCustomInvoice


@skipIfCustomOrganisation
class PaymentInformationViewsTestCase(_BillingTestCase):
    @staticmethod
    def _build_add_url(orga):
        return reverse('billing__create_payment_info', args=(orga.id,))

    @staticmethod
    def _build_add_related_url(invoice):
        return reverse('billing__create_related_payment_info', args=(invoice.id,))

    @staticmethod
    def _build_set_default_url(pi, invoice):
        return reverse('billing__set_default_payment_info', args=(pi.id, invoice.id))

    def test_creation__default_values(self):
        user = self.login_as_root_and_get()

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

        pi = self.get_alone_element(PaymentInformation.objects.all())
        self.assertIs(True, pi.is_default)
        self.assertIsNone(pi.archived)
        self.assertEqual(organisation, pi.organisation)
        self.assertEqual('', pi.bank_code)
        self.assertEqual('', pi.counter_code)
        self.assertEqual('', pi.account_number)
        self.assertEqual('', pi.rib_key)
        self.assertEqual('', pi.banking_domiciliation)
        self.assertEqual('', pi.iban)
        self.assertEqual('', pi.bic)

    def test_creation__filled_values(self):
        user = self.login_as_root_and_get()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        first_pi = PaymentInformation.objects.create(
            organisation=organisation, name='RIB 1', is_default=True,
        )

        url = self._build_add_url(organisation)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            fields = response1.context['form'].fields
        self.assertIn('name', fields)
        self.assertNotIn('archived', fields)

        # ---
        bank_code = 'BANK'
        counter_code = 'COUNTER'
        account_number = 'ACCOUNT'
        key = '12345'
        domiciliation = 'DOM'
        iban = 'IBAN'
        bic = 'BIC'
        self.assertNoFormError(self.client.post(
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
        ))

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

    def test_creation__bad_entity_type(self):
        "Related is not an organisation."
        user = self.login_as_root_and_get()
        self.assertGET404(self._build_add_url(user.linked_contact))

    def test_related_creation(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Organisation, Invoice],
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'], model=Organisation)
        self.add_credentials(user.role, all=['VIEW', 'CHANGE'],         model=Invoice)

        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Playstations')
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

        pi = self.get_alone_element(PaymentInformation.objects.filter(organisation=source.id))
        self.assertIs(True, pi.is_default)
        self.assertEqual(pi, self.refresh(invoice).payment_info)

        # Not a billing doc
        self.assertGET404(self._build_add_related_url(source))

    def test_related_creation__forbidden(self):
        "Credentials for source."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Organisation, Invoice],
        )
        self.add_credentials(user.role, all=['VIEW', 'LINK'], model=Organisation)  # Not 'CHANGE'
        self.add_credentials(user.role, all=['VIEW', 'CHANGE'], model=Invoice)

        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Playstations')
        self.assertGET403(self._build_add_related_url(invoice))

    def test_edition__is_default(self):
        user = self.login_as_root_and_get()

        organisation = Organisation.objects.create(user=user, name='Nintendo')
        pi = PaymentInformation.objects.create(organisation=organisation, name='RIB 1')
        self.assertTrue(pi.is_default)

        url = pi.get_edit_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/edit-popup.html')
        self.assertEqual(
            _('Payment information for «{entity}»').format(entity=organisation),
            response1.context.get('title'),
        )

        with self.assertNoException():
            fields = response1.context['form'].fields
        self.assertIn('name',    fields)
        self.assertIn('rib_key', fields)
        self.assertNotIn('is_default', fields)
        self.assertNotIn('is_archived', fields)

        # POST ---
        rib_key = '00'
        name = f'RIB of {organisation}'
        bic = 'pen?'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'user':    user.pk,
                'name':    name,
                'rib_key': rib_key,
                'bic':     bic,
            },
        ))

        pi = self.refresh(pi)
        self.assertIs(True, pi.is_default)
        self.assertIsNone(pi.archived)
        self.assertEqual(name,    pi.name)
        self.assertEqual(rib_key, pi.rib_key)
        self.assertEqual(bic,     pi.bic)

    def test_edition__becomes_default(self):
        user = self.login_as_root_and_get()

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

    def test_edition__archived(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Nintendo')

        create_pi = PaymentInformation.objects.create
        pi1 = create_pi(organisation=orga, name='RIB 1', is_default=True)
        create_pi(organisation=orga, name='RIB 2', is_default=True)
        self.assertFalse(self.refresh(pi1).is_default)

        url = pi1.get_edit_absolute_url()
        self.assertGET200(url)

        # ---
        data = {'user': user.pk, 'name': 'RIB #1'}

        err_response = self.assertPOST200(
            url, data={**data, 'is_default': True, 'is_archived': True},
        )
        self.assertFormError(
            err_response.context['form'],
            field='is_archived',
            errors=_('You cannot archive the default account'),
        )

        # ---
        self.assertNoFormError(self.client.post(
            url, data={**data, 'is_archived': True},
        ))
        pi1 = self.refresh(pi1)
        self.assertFalse(pi1.is_default)
        self.assertDatetimesAlmostEqual(now(), pi1.archived)

        # ---
        self.assertNoFormError(self.client.post(
            url, data={**data, 'is_archived': False},
        ))
        self.assertIsNone(self.refresh(pi1).archived)

    @skipIfCustomInvoice
    def test_set_default_in_invoice(self):
        user = self.login_as_root_and_get()

        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Playstations')
        pinfo = PaymentInformation.objects.create(organisation=source, name='RIB sony')
        url = self._build_set_default_url(pinfo, invoice)
        self.assertGET405(url)
        self.assertPOST200(url)
        self.assertEqual(pinfo, self.refresh(invoice).payment_info)

    @skipIfCustomInvoice
    def test_set_default_in_invoice__not_emitter(self):
        user = self.login_as_root_and_get()

        other = Organisation.objects.create(user=user, name='Sega')
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Playstations')

        create_pi = PaymentInformation.objects.create
        pi_target = create_pi(organisation=target, name='RIB nintendo')
        pi_source = create_pi(organisation=source, name='RIB sony')
        pi_other  = create_pi(organisation=other,  name='RIB sega')

        def assertPostStatus(code, pi):
            self.assertEqual(
                code,
                self.client.post(self._build_set_default_url(pi, invoice)).status_code
            )

        assertPostStatus(409, pi_target)
        assertPostStatus(409, pi_other)
        assertPostStatus(200, pi_source)

    @skipIfCustomInvoice
    def test_set_default_in_invoice__trashed_organisation(self):
        user = self.login_as_root_and_get()

        invoice, source = self.create_invoice_n_orgas(user=user, name='Playstations')[:2]
        pinfo = PaymentInformation.objects.create(organisation=source, name='RIB sony')

        source.trash()

        self.assertPOST403(self._build_set_default_url(pinfo, invoice))
        self.assertNotEqual(pinfo, self.refresh(invoice).payment_info)

    @skipIfCustomInvoice
    def test_set_default_in_invoice__field_is_hidden(self):
        "'payment_info' is hidden."
        user = self.login_as_root_and_get()

        invoice, sony_source = self.create_invoice_n_orgas(user=user, name='Playstations')[:2]
        pi_sony = PaymentInformation.objects.create(organisation=sony_source, name='RIB sony')

        FieldsConfig.objects.create(
            content_type=Invoice,
            descriptions=[('payment_info', {FieldsConfig.HIDDEN: True})],
        )

        self.assertPOST409(self._build_set_default_url(pi_sony, invoice))

    @skipIfCustomInvoice
    def test_set_default_in_invoice__archived(self):
        user = self.login_as_root_and_get()

        invoice, source = self.create_invoice_n_orgas(user=user, name='Playstations')[:2]

        create_pinfo = partial(PaymentInformation.objects.create, organisation=source)
        create_pinfo(name='RIB sony #1')
        pi2 = create_pinfo(name='RIB sony #2', archived=now())

        response = self.client.post(self._build_set_default_url(pi2, invoice))
        self.assertContains(
            response=response, status_code=409, text=_('This account is archived'),
        )

    # TODO?
    # def test_inneredit(self):
    #     user = self.login()
    #
    #     organisation = Organisation.objects.create(user=user, name='Nintendo')
    #     pi = PaymentInformation.objects.create(organisation=organisation, name='RIB 1')
    #
    #     build_uri = self.build_inneredit_uri
    #     field_name = 'name'
    #     uri = build_uri(pi, field_name)
    #     self.assertGET200(uri)
    #
    #     name = pi.name + ' (default)'
    #     response = self.client.post(
    #         # url,
    #         uri,
    #         data={
    #             # 'entities_lbl': [str(pi)],
    #             # 'field_value':  name,
    #             field_name: name,
    #         },
    #     )
    #     self.assertNoFormError(response)
    #     self.assertEqual(name, self.refresh(pi).name)
    #
    #     # self.assertGET(400, build_url(pi, 'organisation'))
    #     self.assertGET404(build_uri(pi, 'organisation'))
