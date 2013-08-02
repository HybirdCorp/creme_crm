# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from django.utils.translation import ugettext as _

    from creme.creme_core.models import Relation, Currency
    from creme.persons.models import Organisation

    from ..models import CreditNoteStatus, CreditNote, ProductLine
    from ..constants import REL_SUB_CREDIT_NOTE_APPLIED
    from .base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('CreditNoteTestCase',)


class CreditNoteTestCase(_BillingTestCase):
    def setUp(self):
        self.login()
    
    def _build_deleterelated_url(self, credit_note, invoice):
        return '/billing/credit_note/delete_related/%(credit_note)d/from/%(invoice)d/' % {'credit_note': credit_note.id,
                                                                                          'invoice': invoice.id,
                                                                                         }


    def create_credit_note(self, name, source, target, currency=None, discount=Decimal(), user=None, status=None):
        user = user or self.user
        status = status or CreditNoteStatus.objects.all()[0]
        currency = currency or Currency.objects.all()[0]
        response = self.client.post('/billing/credit_note/add', follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        discount,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        credit_note = self.get_object_or_fail(CreditNote, name=name)
        self.assertRedirects(response, credit_note.get_absolute_url())

        return credit_note

    def create_credit_note_n_orgas(self, name, user=None, status=None, **kwargs):
        user = user or self.user
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        credit_note = self.create_credit_note(name, source, target, user=user, status=status, **kwargs)

        return credit_note, source, target

    def assertInvoiceTotalToPay(self, invoice, total):
        invoice = self.refresh(invoice)
        expected_total = Decimal(total)
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_createview01(self):
        "Credit note total < billing document total where the credit note is applied"
        self.assertGET200('/billing/credit_note/add')

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("299"))

        # TODO the credit note must be valid : Status OK (not out of date or consumed), Target = Billing document's target and currency = billing document's currency
        # Theses rules must be applied with q filter on list view before selection
        Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                               )

        invoice = self.refresh(invoice)
        expected_total = Decimal('1')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_createview02(self):
        "Credit note total > document billing total where the credit note is applied"
        user = self.user
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("301"))

        Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                               )

        invoice = self.refresh(invoice)
        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_unlink_from_invoice(self):
        user = self.user
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        self.assertEqual([], invoice.get_credit_notes())

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("60"))

        r = Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                    type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                                   )
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)
        self.assertEqual([credit_note], self.refresh(invoice).get_credit_notes())

        r.delete()
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)
        self.assertEqual([], self.refresh(invoice).get_credit_notes())

    def test_trash_linked_to_invoice(self):
        user = self.user
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("60"))

        Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                               )
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)

        credit_note.trash()
        self.assertTrue(self.refresh(credit_note).is_deleted)
        self.assertEqual([], self.refresh(invoice).get_credit_notes())
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note.restore()
        self.assertFalse(self.refresh(credit_note).is_deleted)
        self.assertEqual([credit_note], self.refresh(invoice).get_credit_notes())
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)

    def test_delete_status01(self):
        status = CreditNoteStatus.objects.create(name='OK')
        self.assertDeleteStatusOK(status, 'credit_note_status')

    def test_delete_status02(self):
        status = CreditNoteStatus.objects.create(name='OK')
        credit_note = self.create_credit_note_n_orgas('Credit Note 001', status=status)[0]

        self.assertDeleteStatusKO(status, 'credit_note_status', credit_note)

    def test_addrelated_view(self):
        "attach credit note to existing invoice"
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.get_target()
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        self.assertGET200('/billing/credit_note/add_related_to/%d/' % invoice.id)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=invoice_target)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 300)

        response = self.client.post('/billing/credit_note/add_related_to/%d/' % invoice.id, follow=True,
                                    data={'credit_notes':    '[%s]' % credit_note.id,}
                                   )
        self.assertNoFormError(response)

        self.assertEqual(1, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 250)

        # check invoice view (bug in block_credit_note.html)
        self.assertGET200('/billing/invoice/%d' % invoice.id)

    def test_addrelated_view_no_invoice(self):
        "cannot attach credit note to invalid invoice"
        self.assertGET404('/billing/credit_note/add_related_to/%d/' % 12445)

    def test_addrelated_view_not_same_currency(self):
        "cannot attach credit note in US Dollar to invoice in Euro"
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)
        us_dollar = Currency.objects.all()[1]

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.get_target()
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        self.assertGET200('/billing/credit_note/add_related_to/%d/' % invoice.id)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=invoice_target, currency=us_dollar)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 300)

        response = self.client.post('/billing/credit_note/add_related_to/%d/' % invoice.id, follow=True,
                                    data={'credit_notes':    '[%s]' % credit_note.id,}
                                   )
        self.assertFormError(response, 'form', 'credit_notes', [_(u"This entity doesn't exist.")])

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 300)

        # check invoice view (bug in block_credit_note.html)
        self.assertGET200('/billing/invoice/%d' % invoice.id)

    def test_addrelated_view_already_linked(self):
        "cannot attach credit note in US Dollar to invoice in Euro"
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)
        us_dollar = Currency.objects.all()[1]

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.get_target()
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        self.assertGET200('/billing/credit_note/add_related_to/%d/' % invoice.id)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=invoice_target, currency=us_dollar)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                               )

        self.assertEqual(1, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 250)

        response = self.client.post('/billing/credit_note/add_related_to/%d/' % invoice.id, follow=True,
                                    data={'credit_notes':    '[%s]' % credit_note.id,}
                                   )
        self.assertFormError(response, 'form', 'credit_notes', [_(u"This entity doesn't exist.")])

        self.assertEqual(1, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 250)

        # check invoice view (bug in block_credit_note.html)
        self.assertGET200('/billing/invoice/%d' % invoice.id)

    def test_addrelated_view_already_not_same_target(self):
        "cannot attach credit note in US Dollar to invoice in Euro"
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal("200"))

        self.assertGET200('/billing/credit_note/add_related_to/%d/' % invoice.id)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note_target = Organisation.objects.create(user=user, name='Organisation 004')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=credit_note_target)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 300)

        response = self.client.post('/billing/credit_note/add_related_to/%d/' % invoice.id, follow=True,
                                    data={'credit_notes':    '[%s]' % credit_note.id,}
                                   )
        self.assertFormError(response, 'form', 'credit_notes', [_(u"This entity doesn't exist.")])

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 300)

    def test_deleterelated_view(self):
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.get_target()
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=invoice_target)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                               )

        self.assertEqual(1, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 50)

        response = self.client.post(self._build_deleterelated_url(credit_note, invoice), follow=True)

        self.assertNoFormError(response)

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 100)

    def test_deleterelated_view_not_exists(self):
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.get_target()
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=invoice_target)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 100)

        self.assertPOST404(self._build_deleterelated_url(credit_note, invoice), follow=True)

        self.assertEqual(0, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 100)

    def test_deleterelated_view_not_allowed(self):
        user = self.user
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.get_target()
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal("100"))

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note('Credit Note 001', source=credit_note_source, target=invoice_target)
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal("50"))

        Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
                                type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
                               )

        self.assertEqual(1, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 50)

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        self.assertPOST403(self._build_deleterelated_url(credit_note, invoice), follow=True)

        self.assertEqual(1, Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count())
        self.assertInvoiceTotalToPay(invoice, 50)


    #TODO: complete (other views)