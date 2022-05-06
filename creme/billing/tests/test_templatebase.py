# -*- coding: utf-8 -*-

from datetime import date, timedelta
from functools import partial

from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.creme_core.core.function_field import function_field_registry
from creme.persons.tests.base import skipIfCustomOrganisation

from ..models import (
    AdditionalInformation,
    CreditNoteStatus,
    InvoiceStatus,
    PaymentTerms,
    QuoteStatus,
    SalesOrderStatus,
)
from .base import (
    Address,
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomQuote,
    skipIfCustomSalesOrder,
    skipIfCustomTemplateBase,
)


@skipIfCustomOrganisation
@skipIfCustomTemplateBase
class TemplateBaseTestCase(_BillingTestCase):
    STATUS_KEY = 'cform_extra-billing_template_status'

    def setUp(self):
        super().setUp()
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        self.source = create_orga(name='Source')
        self.target = create_orga(name='Target')

    def _create_templatebase(self, model, status_id, comment='', **kwargs):
        return TemplateBase.objects.create(
            user=self.user,
            ct=model,
            status_id=status_id,
            comment=comment,
            source=self.source,
            target=self.target,
            **kwargs
        )

    def test_detailview(self):
        invoice_status1 = self.get_object_or_fail(InvoiceStatus, pk=3)
        tpl = self._create_templatebase(Invoice, invoice_status1.id)
        response = self.assertGET200(tpl.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_template.html')

    def test_status_function_field(self):
        invoice_status = self.get_object_or_fail(InvoiceStatus, pk=3)
        tpl = self._create_templatebase(Invoice, invoice_status.id)

        with self.assertNoException():
            funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        self.assertIsNotNone(funf)

        with self.assertNumQueries(1):
            status_str = funf(tpl, self.user).for_html()

        self.assertEqual(str(invoice_status), status_str)

        with self.assertNumQueries(0):
            funf(tpl, self.user).for_html()

    @skipIfCustomInvoice
    def test_create_invoice01(self):
        invoice_status = self.get_object_or_fail(InvoiceStatus, pk=3)
        comment = '*Insert a comment here*'
        tpl = self._create_templatebase(
            Invoice, invoice_status.id, comment,
            additional_info=AdditionalInformation.objects.all()[0],
            payment_terms=PaymentTerms.objects.all()[0],
        )
        address_count = Address.objects.count()

        self.assertEqual('', tpl.number)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertIsInstance(invoice, Invoice)
        self.assertEqual(comment, invoice.comment)
        self.assertEqual(invoice_status, invoice.status)
        self.assertEqual(tpl.additional_info, invoice.additional_info)
        self.assertEqual(tpl.payment_terms,   invoice.payment_terms)
        self.assertEqual(self.source, invoice.source)
        self.assertEqual(self.target, invoice.target)

        self.assertEqual('0', invoice.number)
        self.assertEqual(date.today(), invoice.issuing_date)
        self.assertEqual(invoice.issuing_date + timedelta(days=30), invoice.expiration_date)

        self.assertEqual(address_count + 2, Address.objects.count())

    @skipIfCustomInvoice
    def test_create_invoice02(self):
        "Bad status id."
        pk = 12
        self.assertFalse(InvoiceStatus.objects.filter(pk=pk))

        tpl = self._create_templatebase(Invoice, pk)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertEqual(1, invoice.status_id)

    @skipIfCustomInvoice
    @override_settings(INVOICE_NUMBER_PREFIX='INV')
    def test_create_invoice03(self):
        "Source is managed."
        self._set_managed(self.source)

        invoice_status = self.get_object_or_fail(InvoiceStatus, pk=3)

        tpl = self._create_templatebase(Invoice, invoice_status.id)
        self.assertEqual('', tpl.number)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertIsInstance(invoice, Invoice)
        self.assertEqual('INV1', invoice.number)

    @skipIfCustomInvoice
    def test_create_invoice04(self):
        "Source is not managed + fallback number."
        invoice_status = self.get_object_or_fail(InvoiceStatus, pk=3)
        number = 'INV132'
        tpl = self._create_templatebase(Invoice, invoice_status.id, number=number)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertEqual(number, invoice.number)

    @skipIfCustomQuote
    def test_create_quote01(self):
        quote_status = self.get_object_or_fail(QuoteStatus, pk=2)
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(Quote, quote_status.id, comment)

        with self.assertNoException():
            quote = tpl.create_entity()

        self.assertIsInstance(quote, Quote)
        self.assertEqual(comment, quote.comment)
        self.assertEqual(quote_status, quote.status)

    @skipIfCustomQuote
    def test_create_quote02(self):
        "Bad status id."
        pk = 8
        self.assertFalse(QuoteStatus.objects.filter(pk=pk))

        tpl = self._create_templatebase(Quote, pk)

        with self.assertNoException():
            quote = tpl.create_entity()

        status = quote.status
        self.assertIsNotNone(status)
        self.assertEqual(pk,    status.id)
        self.assertEqual(_('N/A'), status.name)

    @skipIfCustomQuote
    @override_settings(QUOTE_NUMBER_PREFIX='QU')
    def test_create_quote03(self):
        "Source is managed."
        self._set_managed(self.source)

        quote_status = self.get_object_or_fail(QuoteStatus, pk=2)
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(Quote, quote_status.id, comment)

        with self.assertNoException():
            quote = tpl.create_entity()

        self.assertIsInstance(quote, Quote)
        self.assertEqual(comment, quote.comment)
        self.assertEqual(quote_status, quote.status)
        self.assertEqual('QU1', quote.number)

    @skipIfCustomSalesOrder
    def test_create_order01(self):
        order_status = self.get_object_or_fail(SalesOrderStatus, pk=4)
        tpl = self._create_templatebase(SalesOrder, order_status.id)

        with self.assertNoException():
            order = tpl.create_entity()

        self.assertIsInstance(order, SalesOrder)
        self.assertEqual(order_status, order.status)

    @skipIfCustomSalesOrder
    def test_create_order02(self):
        "Bad status id."
        pk = 8
        self.assertFalse(SalesOrder.objects.filter(pk=pk))

        tpl = self._create_templatebase(SalesOrder, pk)

        with self.assertNoException():
            order = tpl.create_entity()

        self.assertEqual(1, order.status.id)

    @skipIfCustomCreditNote
    def test_create_cnote(self):
        cnote_status = self.get_object_or_fail(CreditNoteStatus, pk=2)
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(CreditNote, cnote_status.id, comment)

        with self.assertNoException():
            cnote = tpl.create_entity()

        self.assertIsInstance(cnote, CreditNote)
        self.assertEqual(comment, cnote.comment)
        self.assertEqual(cnote_status, cnote.status)

    def test_editview(self):
        user = self.user

        invoice_status1 = self.get_object_or_fail(InvoiceStatus, pk=3)
        invoice_status2 = self.get_object_or_fail(InvoiceStatus, pk=2)

        name = 'My template'
        tpl = self._create_templatebase(Invoice, invoice_status1.id, name=name)

        url = tpl.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            formfields = response1.context['form'].fields
            source_f = formfields[self.SOURCE_KEY]
            target_f = formfields[self.TARGET_KEY]
            status_f = formfields[self.STATUS_KEY]
            number_f = formfields['number']

        self.assertEqual(self.source, source_f.initial)
        self.assertEqual(self.target, target_f.initial)
        self.assertEqual(invoice_status1.id, status_f.initial)
        self.assertEqual(
            _(
                'If a number is given, it will be only used as fallback value '
                'when generating a number in the final recurring entities.'
            ),
            number_f.help_text,
        )

        # ---
        name += ' (edited)'

        create_orga = partial(Organisation.objects.create, user=self.user)
        source2 = create_orga(name='Source Orga 2')
        target2 = create_orga(name='Target Orga 2')

        response2 = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    '2020-10-31',
                'expiration_date': '2020-11-30',
                self.STATUS_KEY:    invoice_status2.id,
                'currency':        tpl.currency_id,
                'discount':        '0',

                self.SOURCE_KEY: source2.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target2),
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, tpl.get_absolute_url())

        tpl = self.refresh(tpl)
        self.assertEqual(name, tpl.name)
        self.assertEqual(date(year=2020, month=11, day=30), tpl.expiration_date)
        self.assertIsNone(tpl.payment_info)
        self.assertEqual(invoice_status2.id, tpl.status_id)

        self.assertEqual(source2, tpl.source)
        self.assertEqual(target2, tpl.target)

    def test_delete_invoice_status(self):
        new_status, other_status = InvoiceStatus.objects.all()[:2]
        status2del = InvoiceStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(Invoice, status2del.id)
        tpl2 = self._create_templatebase(Invoice, other_status.id)
        tpl3 = self._create_templatebase(Quote,   status2del.id)

        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.status = status2del
        invoice.save()

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='invoice_status',
            new_status=new_status,
            doc=invoice,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertEqual(new_status.id, tpl1.status_id)

        tpl2 = self.refresh(tpl2)
        self.assertEqual(other_status.id, tpl2.status_id)

        tpl3 = self.refresh(tpl3)
        self.assertEqual(status2del.id, tpl3.status_id)

    def test_delete_quote_status(self):
        new_status, other_status = QuoteStatus.objects.all()[:2]
        status2del = QuoteStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(Quote,   status2del.id)
        tpl2 = self._create_templatebase(Quote,   other_status.id)
        tpl3 = self._create_templatebase(Invoice, status2del.id)

        quote = self.create_quote_n_orgas('Nerv', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='quote_status',
            new_status=new_status,
            doc=quote,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertEqual(new_status.id, tpl1.status_id)

        tpl2 = self.refresh(tpl2)
        self.assertEqual(other_status.id, tpl2.status_id)

        tpl3 = self.refresh(tpl3)
        self.assertEqual(status2del.id, tpl3.status_id)

    def test_delete_salesorder_status(self):
        new_status, other_status = SalesOrderStatus.objects.all()[:2]
        status2del = SalesOrderStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(SalesOrder, status2del.id)
        tpl2 = self._create_templatebase(SalesOrder, other_status.id)
        tpl3 = self._create_templatebase(Invoice,    status2del.id)

        order = self.create_salesorder_n_orgas('Order', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='sales_order_status',
            new_status=new_status,
            doc=order,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertEqual(new_status.id, tpl1.status_id)

        tpl2 = self.refresh(tpl2)
        self.assertEqual(other_status.id, tpl2.status_id)

        tpl3 = self.refresh(tpl3)
        self.assertEqual(status2del.id, tpl3.status_id)

    def test_delete_creditnote_status(self):
        new_status, other_status = CreditNoteStatus.objects.all()[:2]
        status2del = CreditNoteStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(CreditNote, status2del.id)
        tpl2 = self._create_templatebase(CreditNote, other_status.id)
        tpl3 = self._create_templatebase(Invoice,    status2del.id)

        credit_note = self.create_credit_note_n_orgas('Credit Note', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='credit_note_status',
            new_status=new_status,
            doc=credit_note,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertEqual(new_status.id, tpl1.status_id)

        tpl2 = self.refresh(tpl2)
        self.assertEqual(other_status.id, tpl2.status_id)

        tpl3 = self.refresh(tpl3)
        self.assertEqual(status2del.id, tpl3.status_id)

    # TODO: test form
