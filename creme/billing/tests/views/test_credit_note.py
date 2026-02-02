from datetime import date
from decimal import Decimal
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.billing.constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_CREDIT_NOTE_APPLIED,
)
from creme.billing.models import CreditNoteStatus
from creme.creme_core.models import (
    Currency,
    FakeOrganisation,
    FieldsConfig,
    Relation,
    Vat,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    CreditNote,
    Invoice,
    Organisation,
    ProductLine,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
)


class _BaseCreditNoteViewsTestCase(_BillingTestCase):
    @staticmethod
    def _build_edit_comment_url(credit_note):
        return reverse('billing__edit_cnote_comment', args=(credit_note.id,))

    def assertInvoiceTotalToPay(self, invoice, total):
        invoice = self.refresh(invoice)
        expected_total = Decimal(total)
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNoteMiscViewsTestCase(BrickTestCaseMixin, _BaseCreditNoteViewsTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()

        invoice, emitter, receiver = self.create_invoice_n_orgas(
            user=user, name='Invoice0001', discount=0,
        )
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001', source=emitter, target=receiver,
        )

        response1 = self.assertGET200(credit_note.get_absolute_url())
        tree1 = self.get_html_tree(response1.content)
        self.get_brick_node(tree1, brick=billing_bricks.ProductLinesBrick)
        self.get_brick_node(tree1, brick=billing_bricks.ServiceLinesBrick)
        self.get_brick_node(tree1, brick=billing_bricks.TargetBrick)
        self.get_brick_node(tree1, brick=billing_bricks.TotalBrick)

        hat_brick_node1 = self.get_brick_node(
            tree1, brick=billing_bricks.CreditNoteCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node1, entity=emitter)
        self.assertInstanceLink(hat_brick_node1, entity=receiver)
        self.assertNoInstanceLink(hat_brick_node1, entity=invoice)

        # Invoice is linked ---
        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )
        response2 = self.assertGET200(credit_note.get_absolute_url())
        hat_brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.CreditNoteCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node2, entity=invoice)

    def test_list_view(self):
        user = self.login_as_root_and_get()

        invoice, emitter, receiver = self.create_invoice_n_orgas(
            user=user, name='Invoice0001', discount=0,
        )
        credit_note1 = self.create_credit_note(
            user=user, name='Credit Note 001', source=emitter, target=receiver,
        )
        credit_note2 = self.create_credit_note(
            user=user, name='Credit Note 002', source=emitter, target=receiver,
        )

        response = self.assertGET200(reverse('billing__list_cnotes'))

        with self.assertNoException():
            cnotes_page = response.context['page_obj']

        self.assertEqual(2, cnotes_page.paginator.count)
        self.assertCountEqual(
            [credit_note1, credit_note2],
            cnotes_page.paginator.object_list,
        )


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNoteCreationTestCase(BrickTestCaseMixin, _BaseCreditNoteViewsTestCase):
    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_smaller_total(self):
        "Credit note total < billing document total where the credit note is applied."
        user = self.login_as_root_and_get()
        self.assertGET200(reverse('billing__create_cnote'))

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        create_line(
            related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'),
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('299'),
        )

        # TODO: the credit note must be valid
        #    - Status OK (not out of date or consumed)
        #    - Target = Billing document's target
        #    - currency = billing document's currency
        # These rules must be applied with q filter on list view before selection
        Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )

        invoice = self.refresh(invoice)
        expected_total = Decimal('1')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

        # ---
        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.CreditNotesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Credit Note',
            plural_title='{count} Credit Notes',
        )
        self.assertInstanceLink(brick_node, entity=credit_note)
        self.assertBrickHasAction(
            brick_node,
            url=self._build_edit_comment_url(credit_note),
            action_type='edit',
        )
        # TODO: complete (hidden fields, no view permission)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_greater_total(self):
        "Credit note total > document billing total where the credit note is applied."
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        create_line(
            related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200')
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
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
    def test_negative_total(self):
        "Credit note in a negative Invoice -> a bigger negative Invoice."
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('-100'),
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
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


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNotesLinkingTestCase(_BaseCreditNoteViewsTestCase):
    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_main(self):
        "Attach credit note to existing invoice."
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
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
            user=user, name='Credit Note 001', source=credit_note_source, target=invoice_target,
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

    def test_no_invoice(self):
        "Cannot attach credit note to invalid invoice."
        self.login_as_root()
        self.assertGET404(reverse('billing__link_to_cnotes', args=(12445,)))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_not_same_currency(self):
        "Cannot attach credit note in US Dollar to invoice in Euro."
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )
        us_dollar = Currency.objects.all()[1]

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        self.assertGET200(url)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001',
            source=credit_note_source, target=invoice_target,
            currency=us_dollar,
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
            self.get_form_or_fail(response),
            field='credit_notes',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': credit_note},
        )

        self.assertFalse(Relation.objects.filter(
            object_entity=invoice, subject_entity=credit_note,
        ))
        self.assertInvoiceTotalToPay(invoice, 300)

        # Check invoice view (bug in block_credit_note.html)
        self.assertGET200(invoice.get_absolute_url())

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_already_linked(self):
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )
        us_dollar = Currency.objects.all()[1]

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        self.assertGET200(url)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001',
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
            self.get_form_or_fail(response),
            field='credit_notes',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': credit_note},
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
    def test_already_not_same_target(self):
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        create_line(related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'))
        create_line(related_document=invoice, on_the_fly_item='Otf2', unit_price=Decimal('200'))

        url = reverse('billing__link_to_cnotes', args=(invoice.id,))
        self.assertGET200(url)

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note_target = Organisation.objects.create(user=user, name='Organisation 004')
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001',
            source=credit_note_source, target=credit_note_target,
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
            self.get_form_or_fail(response),
            field='credit_notes',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': credit_note},
        )

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 300)

    @skipIfCustomInvoice
    def test_regular_user(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='*')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertGET200(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    @skipIfCustomInvoice
    def test_credentials(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='!LINK')
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'], model=Organisation)

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertGET403(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    @skipIfCustomInvoice
    def test_bad_related_type(self):
        "No related to a compatible billing entity."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Foo')
        self.assertGET404(reverse('billing__link_to_cnotes', args=(orga.id,)))


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNoteEditionViewsTestCase(_BaseCreditNoteViewsTestCase):
    def test_edition(self):
        user = self.login_as_root_and_get()

        cnote, source, target  = self.create_credit_note_n_orgas(user=user, name='credit Note 001')

        url = cnote.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            number_f = response1.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        name = cnote.name.title()
        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        status = CreditNoteStatus.objects.exclude(id=cnote.status_id)[0]
        response2 = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'name': name,

                'issuing_date':    self.formfield_value_date(2020, 2, 12),
                'expiration_date': self.formfield_value_date(2020, 3, 14),

                'status': status.id,

                'currency': currency.id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response2)

        cnote = self.refresh(cnote)
        self.assertEqual(name,                             cnote.name)
        self.assertEqual(date(year=2020, month=2, day=12), cnote.issuing_date)
        self.assertEqual(date(year=2020, month=3, day=14), cnote.expiration_date)
        self.assertEqual(currency,                         cnote.currency)
        self.assertEqual(status,                           cnote.status)

        self.assertHaveRelation(subject=cnote, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=cnote, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_edit_comment(self):
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=CreditNote,
            descriptions=[('issuing_date', {FieldsConfig.HIDDEN: True})],
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]

        url = self._build_edit_comment_url(credit_note)
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

    def test_edit_comment__hidden(self):
        "'comment' is hidden."
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=CreditNote,
            descriptions=[('comment', {FieldsConfig.HIDDEN: True})],
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        self.assertGET409(self._build_edit_comment_url(credit_note))

    def test_edit_comment__regular_user(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[CreditNote],
        )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        self.assertGET200(self._build_edit_comment_url(credit_note))

    def test_edit_comment__change_perm(self):
        "CHANGE permission is needed."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[CreditNote],
        )
        self.add_credentials(user.role, all=['VIEW', 'LINK'])  # Not 'CHANGE'

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        self.assertGET403(self._build_edit_comment_url(credit_note))


@skipIfCustomOrganisation
@skipIfCustomCreditNote
@skipIfCustomInvoice
@skipIfCustomProductLine
class CreditNoteDeletionTestCase(_BaseCreditNoteViewsTestCase):
    @staticmethod
    def _build_delete_related_url(credit_note, invoice):
        return reverse('billing__delete_related_cnote', args=(credit_note.id, invoice.id))

    def test_delete_related(self):
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001',
            source=credit_note_source, target=invoice_target,
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

        url = self._build_delete_related_url(credit_note, invoice)
        self.assertGET405(url)

        response = self.assertPOST200(url, follow=True)
        self.assertRedirects(response, invoice.get_absolute_url())

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

    def test_delete_related__does_not_exist(self):
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001',
            source=credit_note_source, target=invoice_target,
        )
        create_line(
            related_document=credit_note, on_the_fly_item='Otf3', unit_price=Decimal('50'),
        )

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

        self.assertPOST404(self._build_delete_related_url(credit_note, invoice), follow=True)

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

    def test_delete_related__forbidden(self):
        user = self.login_as_root_and_get()
        create_line = partial(
            ProductLine.objects.create,
            user=user, vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        invoice_target = invoice.target
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )

        credit_note_source = Organisation.objects.create(user=user, name='Organisation 003')
        credit_note = self.create_credit_note(
            user=user, name='Credit Note 001',
            source=credit_note_source, target=invoice_target,
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

        other = self.create_user(role=self.create_role(), password=self.USER_PASSWORD)
        self.client.login(username=other.username, password=self.USER_PASSWORD)

        self.assertPOST403(
            self._build_delete_related_url(credit_note, invoice), follow=True,
        )

        self.assertEqual(
            1,
            Relation.objects.filter(
                object_entity=invoice, subject_entity=credit_note,
            ).count(),
        )
        self.assertInvoiceTotalToPay(invoice, 50)


# TODO: complete (other views)
