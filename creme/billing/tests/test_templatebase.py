# -*- coding: utf-8 -*-

from datetime import date, timedelta
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.models import Relation
from creme.persons.tests.base import skipIfCustomOrganisation

from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from ..models import (
    AdditionalInformation,
    CreditNoteStatus,
    InvoiceStatus,
    PaymentTerms,
    QuoteStatus,
    SalesOrderStatus,
)
from .base import (
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomQuote,
    skipIfCustomSalesOrder,
    skipIfCustomTemplateBase,
)


@skipIfCustomOrganisation
@skipIfCustomTemplateBase
class TemplateBaseTestCase(_BillingTestCase):
    def setUp(self):
        super().setUp()
        self.login()

        create_orga = partial(Organisation.objects.create, user=self.user)
        self.source = create_orga(name='Source')
        self.target = create_orga(name='Target')

    def _create_templatebase(self, model, status_id, comment=''):
        user = self.user
        tpl = TemplateBase.objects.create(user=user,
                                          ct=ContentType.objects.get_for_model(model),
                                          status_id=status_id,
                                          comment=comment,
                                         )

        create_rel = partial(Relation.objects.create, user=user, subject_entity=tpl)
        create_rel(type_id=REL_SUB_BILL_ISSUED,   object_entity=self.source)
        create_rel(type_id=REL_SUB_BILL_RECEIVED, object_entity=self.target)

        return tpl

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
        tpl = self._create_templatebase(Invoice, invoice_status.id, comment)

        tpl.additional_info = AdditionalInformation.objects.all()[0]
        tpl.payment_terms = PaymentTerms.objects.all()[0]
        tpl.save()

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertIsInstance(invoice, Invoice)
        self.assertEqual(comment, invoice.comment)
        self.assertEqual(invoice_status, invoice.status)
        self.assertEqual(tpl.additional_info, invoice.additional_info)
        self.assertEqual(tpl.payment_terms,   invoice.payment_terms)
        self.assertEqual(self.source, invoice.get_source().get_real_entity())
        self.assertEqual(self.target, invoice.get_target().get_real_entity())

        self.assertIsNotNone(invoice.number)
        self.assertEqual(date.today(), invoice.issuing_date)
        self.assertEqual(invoice.issuing_date + timedelta(days=30), invoice.expiration_date)

    @skipIfCustomInvoice
    def test_create_invoice02(self):
        "Bad status id"
        pk = 12
        self.assertFalse(InvoiceStatus.objects.filter(pk=pk))

        tpl = self._create_templatebase(Invoice, pk)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertEqual(1, invoice.status_id)

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
        "Bad status id"
        pk = 8
        self.assertFalse(QuoteStatus.objects.filter(pk=pk))

        tpl = self._create_templatebase(Quote, pk)

        with self.assertNoException():
            quote = tpl.create_entity()

        status = quote.status
        self.assertIsNotNone(status)
        self.assertEqual(pk,    status.id)
        self.assertEqual(_('N/A'), status.name)

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

    def test_delete_invoice_status(self):
        new_status, other_status = InvoiceStatus.objects.all()[:2]
        status2del = InvoiceStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(Invoice, status2del.id)
        tpl2 = self._create_templatebase(Invoice, other_status.id)
        tpl3 = self._create_templatebase(Quote,   status2del.id)

        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.status = status2del
        invoice.save()

        self.assertDeleteStatusOK(status2del=status2del,
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

        self.assertDeleteStatusOK(status2del=status2del,
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

        self.assertDeleteStatusOK(status2del=status2del,
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

        self.assertDeleteStatusOK(status2del=status2del,
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
