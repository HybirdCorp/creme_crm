# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

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

    def create_credit_note_n_orgas(self, name, user=None, status=None):
        user = user or self.user
        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        credit_note = self.create_credit_note(name, source, target, user=user, status=status)

        return credit_note, source, target

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

        r = Relation.objects.create(object_entity=invoice, subject_entity=credit_note,
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

    #TODO: complete (other views)