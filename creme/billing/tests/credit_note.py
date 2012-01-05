# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from creme_core.models import Relation, Currency
    from creme_core.tests.base import CremeTestCase

    from persons.models import Organisation

    from billing.models import *
    from billing.constants import *
    from billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('CreditNoteTestCase',)


class CreditNoteTestCase(_BillingTestCase, CremeTestCase):
    def create_credit_note(self, name, source, target, currency=None, discount=Decimal(), user=None):
        user = user or self.user
        currency = currency or Currency.objects.all()[0]
        response = self.client.post('/billing/credit_note/add', follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          1,
                                          'currency':        currency.id,
                                          'discount':        discount,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   len(response.redirect_chain))

        credit_note = self.get_object_or_fail(CreditNote, name=name)
        self.assertTrue(response.redirect_chain[0][0].endswith('/billing/credit_note/%s' % credit_note.id))

        return credit_note

    def create_credit_note_n_orgas(self, name, user=None):
        user = user or self.user
        create = Organisation.objects.create
        source = create(user=user, name='Source Orga')
        target = create(user=user, name='Target Orga')

        credit_note = self.create_credit_note(name, source, target, user=user)

        return credit_note, source, target

    def test_createview01(self): # credit note total < billing document total where the credit note is applied
        self.login()

        self.assertEqual(200, self.client.get('/billing/credit_note/add').status_code)

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')
        invoice = self.create_invoice('Invoice0001', source, target, discount=0)

        pl1 = ProductLine.objects.create(user=self.user, unit_price=Decimal("100"))
        pl1.related_document = invoice
        pl2 = ProductLine.objects.create(user=self.user, unit_price=Decimal("200"))
        pl2.related_document = invoice

        invoice.save()

        credit_note, source, target = self.create_credit_note_n_orgas('Credit Note 001')
        pl3 = ProductLine.objects.create(user=self.user, unit_price=Decimal("299"))
        pl3.related_document = credit_note

        # TODO the credit note must be valid : Status OK (not out of date or consumed), Target = Billing document's target and currency = billing document's currency
        # Theses rules must be applied with q filter on list view before selection
        Relation.objects.create(object_entity=invoice, subject_entity=credit_note, type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=self.user)

        invoice = self.refresh(invoice)
        self.assertEqual(Decimal('1'), invoice.get_total())
        self.assertEqual(Decimal('1'), invoice.get_total_with_tax())
        # TODO these two last tests are not working for the moment because adding a credit note doesnt contact the billing document (signal or anything else)
        # a billing document save is necessary to update the totals fields after adding him a credit note
#        self.assertEqual(Decimal('1'), invoice.total_no_vat)
#        self.assertEqual(Decimal('1'), invoice.total_vat)

    def test_createview02(self): # credit note total > document billing total where the credit note is applied
        self.login()

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')
        invoice = self.create_invoice('Invoice0001', source, target, discount=0)

        pl1 = ProductLine.objects.create(user=self.user, unit_price=Decimal("100"))
        pl1.related_document = invoice
        pl2 = ProductLine.objects.create(user=self.user, unit_price=Decimal("200"))
        pl2.related_document = invoice

        invoice.save()

        credit_note, source, target = self.create_credit_note_n_orgas('Credit Note 001')
        pl3 = ProductLine.objects.create(user=self.user, unit_price=Decimal("301"))
        pl3.related_document = credit_note

        # TODO the credit note must be valid : Status OK (not out of date or consumed), Target = Billing document's target and currency = billing document's currency
        # Theses rules must be applied with q filter on list view before selection
        Relation.objects.create(object_entity=invoice, subject_entity=credit_note, type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=self.user)

        invoice = self.refresh(invoice)
        self.assertEqual(Decimal('0'), invoice.get_total())
        self.assertEqual(Decimal('0'), invoice.get_total_with_tax())
        # TODO these two last tests are not working for the moment because adding a credit note doesnt contact the billing document (signal or anything else)
        # a billing document save is necessary to update the totals fields after adding him a credit note
#        self.assertEqual(Decimal('0'), invoice.total_no_vat)
#        self.assertEqual(Decimal('0'), invoice.total_vat)

    #TODO: complete (other views)