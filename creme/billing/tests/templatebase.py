# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import Relation
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Organisation

    from ..models import (TemplateBase, Invoice, InvoiceStatus,
                          Quote, QuoteStatus, SalesOrder, SalesOrderStatus)
    from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
    from .base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('TemplateBaseTestCase',)


class TemplateBaseTestCase(_BillingTestCase, CremeTestCase):
    def setUp(self):
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

    def test_create_invoice01(self):
        invoice_status = self.get_object_or_fail(InvoiceStatus, pk=3)
        comment = '*Insert a comment here*'
        tpl = self._create_templatebase(Invoice, invoice_status.id, comment)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertIsInstance(invoice, Invoice)
        self.assertEqual(comment, invoice.comment)
        self.assertEqual(invoice_status, invoice.status)
        self.assertEqual(self.source, invoice.get_source().get_real_entity())
        self.assertEqual(self.target, invoice.get_target().get_real_entity())

    def test_create_invoice02(self):
        "Bad status id"
        pk = 12
        self.assertFalse(InvoiceStatus.objects.filter(pk=pk))

        tpl = self._create_templatebase(Invoice, pk)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertEqual(1, invoice.status_id)

    def test_create_quote01(self):
        quote_status = self.get_object_or_fail(QuoteStatus, pk=2)
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(Quote, quote_status.id, comment)

        with self.assertNoException():
            quote = tpl.create_entity()

        self.assertIsInstance(quote, Quote)
        self.assertEqual(comment, quote.comment)
        self.assertEqual(quote_status, quote.status)

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
        self.assertEqual('N/A', status.name)

    def test_create_order01(self):
        order_status = self.get_object_or_fail(SalesOrderStatus, pk=4)
        tpl = self._create_templatebase(SalesOrder, order_status.id)

        with self.assertNoException():
            order = tpl.create_entity()

        self.assertIsInstance(order, SalesOrder)
        self.assertEqual(order_status, order.status)

    def test_create_order02(self):
        "Bad status id"
        pk = 8
        self.assertFalse(SalesOrder.objects.filter(pk=pk))

        tpl = self._create_templatebase(SalesOrder, pk)

        with self.assertNoException():
            order = tpl.create_entity()

        self.assertEqual(1, order.status.id)

    #TODO: test form
