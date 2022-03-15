# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.models import (
    Currency,
    FakeOrganisation,
    FieldsConfig,
    Relation,
    SetCredentials,
)
from creme.persons.tests.base import skipIfCustomOrganisation

from ..constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_CREDIT_NOTE_APPLIED,
)
from ..models import CreditNoteStatus
from .base import (
    CreditNote,
    Invoice,
    Organisation,
    ProductLine,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
)


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNoteTestCase(_BillingTestCase):
    @staticmethod
    def _build_editcomment_url(credit_note):
        return reverse('billing__edit_cnote_comment', args=(credit_note.id,))

    @staticmethod
    def _build_deleterelated_url(credit_note, invoice):
        return reverse('billing__delete_related_cnote', args=(credit_note.id, invoice.id))

    def assertInvoiceTotalToPay(self, invoice, total):
        invoice = self.refresh(invoice)
        expected_total = Decimal(total)
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_createview01(self):
        "Credit note total < billing document total where the credit note is applied"
        user = self.login()
        self.assertGET200(reverse('billing__create_cnote'))

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        create_line(
            related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'),
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('299'),
        )

        # TODO: the credit note must be valid : Status OK (not out of date or consumed),
        #                                       Target = Billing document's target
        #                                       currency = billing document's currency
        # These rules must be applied with q filter on list view before selection
        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        invoice = self.refresh(invoice)
        expected_total = Decimal('1')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_createview02(self):
        "Credit note total > document billing total where the credit note is applied"
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        create_line(
            related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200')
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('301'),
        )

        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        invoice = self.refresh(invoice)
        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_createview03(self):
        "Credit note in a negative Invoice -> a bigger negative Invoice"
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('-100'),
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('1'),
        )

        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        invoice = self.refresh(invoice)
        expected_total = Decimal('-101')
        self.assertEqual(expected_total, invoice.total_no_vat)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_unlink_from_invoice(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        self.assertListEqual([], invoice.get_credit_notes())

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('60'),
        )

        r = Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)
        self.assertEqual([credit_note], self.refresh(invoice).get_credit_notes())

        r.delete()
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)
        self.assertEqual([], self.refresh(invoice).get_credit_notes())

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_trash_linked_to_invoice(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('60'),
        )

        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)

        credit_note.trash()
        self.assertTrue(self.refresh(credit_note).is_deleted)
        self.assertListEqual([], self.refresh(invoice).get_credit_notes())
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note.restore()
        self.assertFalse(self.refresh(credit_note).is_deleted)
        self.assertListEqual([credit_note], self.refresh(invoice).get_credit_notes())
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)

    # def test_delete_status01(self):
    def test_delete_status(self):
        self.login()

        new_status = CreditNoteStatus.objects.first()
        status2del = CreditNoteStatus.objects.create(name='OK')

        credit_note = self.create_credit_note_n_orgas(
            'Credit Note 001', status=status2del,
        )[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='credit_note_status',
            new_status=new_status,
            doc=credit_note,
        )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_addrelated_view(self):
        "Attach credit note to existing invoice."
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        # invoice_target = invoice.get_target()
        invoice_target = invoice.target
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(
            response, 'creme_core/generics/blockform/link-popup.html',
        )

        context = response.context
        self.assertEqual(
            _('Credit notes for «{entity}»').format(entity=invoice),
            context.get('title')
        )
        self.assertEqual(
            _('Link the credit notes'),
            context.get('submit_label')
        )

        # ---
        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            'Credit Note 001', source=credit_note_source, target=invoice_target,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        self.assertEqual(
            0,
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 300)

        response = self.client.post(
            url, follow=True,
            data={'credit_notes': self.formfield_value_multi_creator_entity(credit_note)},
        )
        self.assertNoFormError(response)

        self.assertEqual(
            1,
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 250)

        # Check invoice view (bug in block_credit_note.html)
        self.assertGET200(invoice.get_absolute_url())

    def test_addrelated_view_no_invoice(self):
        "Cannot attach credit note to invalid invoice."
        self.login()
        self.assertGET404(reverse('billing__link_to_cnotes', args=(12445,)))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_addrelated_view_not_same_currency(self):
        "Cannot attach credit note in US Dollar to invoice in Euro."
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)
        us_dollar = Currency.objects.all()[1]

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        self.assertGET200(url)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            'Credit Note 001',
            source=credit_note_source, target=invoice_target, currency=us_dollar,
        )
        create_line(related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'))

        self.assertFalse(
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ),
        )
        self.assertInvoiceTotalToPay(invoice, 300)

        response = self.client.post(
            url,
            follow=True,
            data={'credit_notes': self.formfield_value_multi_creator_entity(credit_note)},
        )
        self.assertFormError(
            # response, 'form', 'credit_notes', _('This entity does not exist.'),
            response, 'form', 'credit_notes',
            _('«%(entity)s» violates the constraints.') % {'entity': credit_note},
        )

        self.assertFalse(Relation.objects.filter(
            object_entity=invoice, subject_entity=credit_note,
        ))
        self.assertInvoiceTotalToPay(invoice, 300)

        # Check invoice view (bug in block_credit_note.html)
        self.assertGET200(invoice.get_absolute_url())

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_addrelated_view_already_linked(self):
        "Cannot attach credit note in US Dollar to invoice in Euro."
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)
        us_dollar = Currency.objects.all()[1]

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        self.assertGET200(url)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            'Credit Note 001',
            source=credit_note_source,
            target=invoice_target,
            currency=us_dollar,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        self.assertEqual(
            1,
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 250)

        response = self.client.post(
            url, follow=True,
            data={'credit_notes': self.formfield_value_multi_creator_entity(credit_note)},
        )
        self.assertFormError(
            # response, 'form', 'credit_notes', _('This entity does not exist.'),
            response, 'form', 'credit_notes',
            _('«%(entity)s» violates the constraints.') % {'entity': credit_note},
        )

        self.assertEqual(
            1,
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 250)

        # Check invoice view (bug in block_credit_note.html)
        self.assertGET200(invoice.get_absolute_url())

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_addrelated_view_already_not_same_target(self):
        "Cannot attach credit note in US Dollar to invoice in Euro."
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        self.assertGET200(url)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note_target = Organisation.objects.create(user=user, name='Organisation 004')
        credit_note = self.create_credit_note(
            'Credit Note 001', source=credit_note_source, target=credit_note_target,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 300)

        response = self.client.post(
            url, follow=True,
            data={'credit_notes': self.formfield_value_multi_creator_entity(credit_note)},
        )
        self.assertFormError(
            # response, 'form', 'credit_notes', _('This entity does not exist.'),
            response, 'form', 'credit_notes',
            _('«%(entity)s» violates the constraints.') % {'entity': credit_note},
        )

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 300)

    @skipIfCustomInvoice
    def test_addrelated_view_notsuperuser(self):
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        self.assertGET200(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    @skipIfCustomInvoice
    def test_addrelated_view_linkcredentials(self):
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )

        create_sc = partial(
            SetCredentials.objects.create,
            role=self.role, set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            ctype=Organisation,
        )
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                # | EntityCredentials.LINK   # <==
                | EntityCredentials.UNLINK
            ),
        )

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        self.assertGET403(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    def test_editview(self):
        user = self.login()

        credit_note, source, target  = self.create_credit_note_n_orgas('credit Note 001')

        url = credit_note.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            number_f = response1.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        name = credit_note.name.title()
        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        status = CreditNoteStatus.objects.exclude(id=credit_note.status_id)[0]
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'name': name,

                'issuing_date':     '2020-2-12',
                'expiration_date':  '2020-3-14',

                'status': status.id,

                'currency': currency.id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response2)

        credit_note = self.refresh(credit_note)
        self.assertEqual(name,                             credit_note.name)
        self.assertEqual(date(year=2020, month=2, day=12), credit_note.issuing_date)
        self.assertEqual(date(year=2020, month=3, day=14), credit_note.expiration_date)
        self.assertEqual(currency,                         credit_note.currency)
        self.assertEqual(status,                           credit_note.status)

        self.assertRelationCount(1, credit_note, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, credit_note, REL_SUB_BILL_RECEIVED, target)

    @skipIfCustomInvoice
    def test_addrelated_view_badrelated(self):
        "No related to a compatible billing entity"
        user = self.login()
        orga = FakeOrganisation.objects.create(user=user, name='Foo')
        self.assertGET404(reverse('billing__link_to_cnotes', args=(orga.id,)))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_deleterelated_view(self):
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            'Credit Note 001', source=credit_note_source, target=invoice_target,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        self.assertEqual(
            1,
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 50)

        url = self._build_deleterelated_url(credit_note, invoice)
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, invoice.get_absolute_url())

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_deleterelated_view_not_exists(self):
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            'Credit Note 001', source=credit_note_source, target=invoice_target,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

        self.assertPOST404(self._build_deleterelated_url(credit_note, invoice), follow=True)

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_deleterelated_view_not_allowed(self):
        user = self.login()
        create_line = partial(ProductLine.objects.create, user=user)

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            'Credit Note 001', source=credit_note_source, target=invoice_target,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        self.assertEqual(
            1,
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 50)

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        self.assertPOST403(
            self._build_deleterelated_url(credit_note, invoice), follow=True,
        )

        self.assertEqual(
            1,
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 50)

    def test_editcomment01(self):
        self.login()
        FieldsConfig.objects.create(
            content_type=CreditNote,
            descriptions=[('issuing_date', {FieldsConfig.HIDDEN: True})],
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]

        url = self._build_editcomment_url(credit_note)
        response = self.assertGET200(url)
        self.assertTemplateUsed(
            response, 'creme_core/generics/blockform/edit-popup.html',
        )
        self.assertEqual(
            _('Edit «{object}»').format(object=credit_note),
            response.context.get('title'),
        )

        # ---
        comment = 'Special gift'
        self.assertNoFormError(self.client.post(url, data={'comment': comment}))
        self.assertEqual(comment, self.refresh(credit_note).comment)

    def test_editcomment02(self):
        "'comment' is hidden."
        self.login()
        FieldsConfig.objects.create(
            content_type=CreditNote,
            descriptions=[('comment', {FieldsConfig.HIDDEN: True})],
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        self.assertGET409(self._build_editcomment_url(credit_note))

    def test_editcomment03(self):
        "Not super-user."
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[CreditNote],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        self.assertGET200(self._build_editcomment_url(credit_note))

    def test_editcomment04(self):
        "CHANGE permission is needed."
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[CreditNote],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,  # Not CHANGE
            set_type=SetCredentials.ESET_ALL,
        )

        credit_note = self.create_credit_note_n_orgas('Credit Note 001')[0]
        self.assertGET403(self._build_editcomment_url(credit_note))

    # TODO: complete (other views)
