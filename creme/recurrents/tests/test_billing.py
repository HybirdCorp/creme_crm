from functools import partial

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.constants import DEFAULT_VAT
from creme.creme_core.models import Currency, Vat
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.persons import get_address_model, get_organisation_model

from .base import RecurrentGenerator, RecurrentsTestCase, skipIfCustomGenerator

Address = get_address_model()
Organisation = get_organisation_model()

if apps.is_installed('creme.billing'):
    from creme.billing import (
        get_credit_note_model,
        get_invoice_model,
        get_quote_model,
        get_sales_order_model,
        get_template_base_model,
    )
    from creme.billing.models import (
        CreditNoteStatus,
        InvoiceStatus,
        QuoteStatus,
        SalesOrderStatus,
    )
    from creme.billing.tests.base import (
        skipIfCustomCreditNote,
        skipIfCustomInvoice,
        skipIfCustomQuote,
        skipIfCustomSalesOrder,
    )

    CreditNote = get_credit_note_model()
    Invoice = get_invoice_model()
    Quote = get_quote_model()
    SalesOrder = get_sales_order_model()
    TemplateBase = get_template_base_model()
else:
    from unittest import skip

    def skipIfCustomCreditNote(test_func):
        return skip('App "billing" not installed')(test_func)

    def skipIfCustomInvoice(test_func):
        return skip('App "billing" not installed')(test_func)

    def skipIfCustomQuote(test_func):
        return skip('App "billing" not installed')(test_func)

    def skipIfCustomSalesOrder(test_func):
        return skip('App "billing" not installed')(test_func)


@skipIfNotInstalled('creme.billing')
@skipIfCustomGenerator
class RecurrentsBillingTestCase(RecurrentsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        Vat.objects.get_or_create(is_default=True, defaults={'value': DEFAULT_VAT})

        cls.ADD_URL = reverse('recurrents__create_generator')

    def _aux_test_create(self, model, status_model, target_has_addresses=False):
        user = self.login_as_root_and_get()
        url = self.ADD_URL
        self.assertGET200(url)

        gen_name = f'Recurrent {model.__name__}'
        ct = ContentType.objects.get_for_model(model)
        response1 = self.client.post(
            url,
            data={
                'recurrent_generator_wizard-current_step': 0,

                '0-user':             user.id,
                '0-name':             gen_name,
                '0-first_generation': self.formfield_value_datetime(
                    year=2014, month=7, day=8, hour=11,
                ),
                '0-periodicity_0':    'months',
                '0-periodicity_1':    '1',

                self.CTYPE_KEY: ct.id,
            },
        )
        self.assertNoWizardFormError(response1)

        with self.assertNoException():
            number_f = response1.context['form'].fields['number']

        self.assertEqual(
            _(
                'If a number is given, it will be only used as fallback value '
                'when generating a number in the final recurring entities.'
            ),
            number_f.help_text,
        )

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        if target_has_addresses:
            create_address = Address.objects.create
            target.billing_address = create_address(
                name='Billing address 01',
                address='BA1 - Address', po_box='BA1 - PO box',
                zipcode='BA1 - Zip code', city='BA1 - City',
                department='BA1 - Department',
                state='BA1 - State', country='BA1 - Country',
                owner=target,
            )
            target.shipping_address = create_address(
                name='Shipping address 01',
                address='SA1 - Address', po_box='SA1 - PO box',
                zipcode='SA1 - Zip code', city='SA1 - City',
                department='SA1 - Department',
                state='SA1 - State', country='SA1 - Country',
                owner=target,
            )
            target.save()

        tpl_name = 'Subscription invoice'
        status = status_model.objects.all()[0]
        currency = Currency.objects.all()[0]
        discount = 0
        response2 = self.client.post(
            url, follow=True,
            data={
                'recurrent_generator_wizard-current_step': 1,

                '1-user':     user.id,
                '1-name':     tpl_name,
                '1-currency': currency.id,
                '1-discount': discount,

                '1-cform_extra-billing_template_status': status.id,

                '1-cform_extra-billing_source': source.id,
                '1-cform_extra-billing_target': self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoWizardFormError(response2)

        gen = self.get_object_or_fail(RecurrentGenerator, name=gen_name)
        tpl = self.get_object_or_fail(TemplateBase, name=tpl_name)

        self.assertEqual(user, gen.user)
        self.assertEqual(ct,   gen.ct)
        self.assertDictEqual(
            {'type': 'months', 'value': 1}, gen.periodicity.as_dict(),
        )
        self.assertEqual(
            self.create_datetime(year=2014, month=7, day=8, hour=11),
            gen.first_generation,
        )
        self.assertIsNone(gen.last_generation)
        self.assertEqual(tpl, gen.template.get_real_entity())
        self.assertTrue(gen.is_working)

        self.assertEqual(user,        tpl.user)
        self.assertEqual(currency,    tpl.currency)
        self.assertEqual(status.uuid, tpl.status_uuid)
        self.assertEqual(discount,    tpl.discount)
        self.assertEqual(source,      tpl.source)
        self.assertEqual(target,      tpl.target)

        billing_address = tpl.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(tpl, billing_address.owner)

        shipping_address = tpl.shipping_address
        self.assertIsInstance(shipping_address, Address)
        self.assertEqual(tpl, shipping_address.owner)

        if target_has_addresses:
            b_addr = target.billing_address
            self.assertEqual(b_addr.name, billing_address.name)
            self.assertEqual(b_addr.city, billing_address.city)

            s_addr = target.shipping_address
            self.assertEqual(s_addr.name,       shipping_address.name)
            self.assertEqual(s_addr.department, shipping_address.department)
        else:
            self.assertEqual(_('Billing address'), billing_address.name)
            self.assertFalse(billing_address.city)

            self.assertEqual(_('Shipping address'), shipping_address.name)
            self.assertFalse(shipping_address.city)

        self._generate_docs()

        new_entities = model.objects.all()
        self.assertEqual(1, len(new_entities))

    @skipIfCustomInvoice
    def test_create_invoice01(self):
        self._aux_test_create(Invoice, InvoiceStatus)

    @skipIfCustomInvoice
    def test_create_invoice02(self):
        self._aux_test_create(Invoice, InvoiceStatus, target_has_addresses=True)

    @skipIfCustomQuote
    def test_create_quote(self):
        self._aux_test_create(Quote, QuoteStatus)

    @skipIfCustomSalesOrder
    def test_create_order(self):
        self._aux_test_create(SalesOrder, SalesOrderStatus)

    @skipIfCustomCreditNote
    def test_create_note(self):
        self._aux_test_create(CreditNote, CreditNoteStatus)

    def test_create_credentials01(self):
        "Creation credentials for generated models."
        user = self.login_as_standard(
            allowed_apps=['persons', 'recurrents'],
            creatable_models=[RecurrentGenerator, Quote],  # Not Invoice
        )

        url = self.ADD_URL
        self.assertGET200(url)

        def post(model):
            ct = ContentType.objects.get_for_model(model)
            return self.client.post(
                url,
                data={
                    'recurrent_generator_wizard-current_step': 0,

                    '0-user': user.id,
                    '0-name': 'Recurrent billing obj',

                    '0-cform_extra-recurrents_ctype': ct.id,

                    '0-first_generation': self.formfield_value_datetime(
                        year=2014, month=7, day=8, hour=11,
                    ),

                    '0-periodicity_0': 'weeks',
                    '0-periodicity_1': '3',
                },
            )

        response = post(Invoice)

        # TODO: in CremeTestCase ??
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            errors = response.context['wizard']['form'].errors

        self.assertDictEqual(
            {
                'cform_extra-recurrents_ctype': [_(
                    'Select a valid choice. '
                    'That choice is not one of the available choices.'
                )],
            },
            errors,
        )

        response = post(Quote)
        self.assertNoWizardFormError(response)

    @skipIfCustomQuote
    def test_create_credentials02(self):
        "App credentials."
        self.login_as_standard(
            allowed_apps=['persons'],  # Not 'recurrents'
            creatable_models=[RecurrentGenerator, Quote],
        )

        self.assertGET403(self.ADD_URL)

    @skipIfCustomQuote
    def test_create_credentials03(self):
        "Creation credentials for generator."
        self.login_as_standard(
            allowed_apps=['persons', 'recurrents'],
            creatable_models=[Quote],  # Not RecurrentGenerator
        )
        self.assertGET403(self.ADD_URL)
