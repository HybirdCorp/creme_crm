from datetime import date
from decimal import Decimal
# from uuid import uuid4
from functools import partial

from django.template import Context, Template
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    BrickDetailviewLocation,
    Currency,
    FakeOrganisation,
    FieldsConfig,
    Relation,
    Vat,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from .. import bricks as billing_bricks
from ..constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_CREDIT_NOTE_APPLIED,
    UUID_CNOTE_STATUS_DRAFT,
)
from ..models import CreditNoteStatus, Line
# from .base import TemplateBase
from .base import (
    Address,
    CreditNote,
    Invoice,
    Organisation,
    ProductLine,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomServiceLine,
)


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNoteTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_edit_comment_url(credit_note):
        return reverse('billing__edit_cnote_comment', args=(credit_note.id,))

    @staticmethod
    def _build_delete_related_url(credit_note, invoice):
        return reverse('billing__delete_related_cnote', args=(credit_note.id, invoice.id))

    def assertInvoiceTotalToPay(self, invoice, total):
        invoice = self.refresh(invoice)
        expected_total = Decimal(total)
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_status(self):
        statuses = [*CreditNoteStatus.objects.all()]
        self.assertEqual(4, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertUUIDEqual(UUID_CNOTE_STATUS_DRAFT, default_status.uuid)

        # New default status => previous default status is updated
        new_status1 = CreditNoteStatus.objects.create(name='OK', is_default=True)
        self.assertTrue(self.refresh(new_status1).is_default)
        self.assertEqual(5, CreditNoteStatus.objects.count())
        self.assertFalse(
            CreditNoteStatus.objects.exclude(id=new_status1.id).filter(is_default=True)
        )

        # No default status is found => new one is default one
        CreditNoteStatus.objects.update(is_default=False)
        new_status2 = CreditNoteStatus.objects.create(name='KO', is_default=False)
        self.assertTrue(self.refresh(new_status2).is_default)

    def test_status_render(self):
        user = self.get_root_user()
        status = CreditNoteStatus.objects.create(name='OK', color='00FF00')
        order = CreditNote(user=user, name='OK Note', status=status)

        with self.assertNoException():
            render = Template(
                r'{% load creme_core_tags %}'
                r'{% print_field object=order field="status" tag=tag %}'
            ).render(Context({
                'user': user,
                'order': order,
                'tag': ViewTag.HTML_DETAIL,
            }))

        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            render,
        )

    def test_detailview(self):
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

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_creation__smaller_total(self):
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
    def test_creation__greater_total(self):
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
    def test_creation__negative_total(self):
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

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_unlink_from_invoice(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertListEqual([], invoice.get_credit_notes())

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
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
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        create_line = partial(ProductLine.objects.create, user=user)
        create_line(
            related_document=invoice, on_the_fly_item='Otf1', unit_price=Decimal('100'),
        )
        self.assertEqual(Decimal('100'), self.refresh(invoice).total_no_vat)

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
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

        self.assertTrue(getattr(credit_note.trash, 'alters_data', False))

        credit_note.restore()
        self.assertFalse(self.refresh(credit_note).is_deleted)
        self.assertListEqual([credit_note], self.refresh(invoice).get_credit_notes())
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)

        self.assertTrue(getattr(credit_note.restore, 'alters_data', False))

    def test_delete(self):
        user = self.login_as_root_and_get()
        credit_note, source, target = self.create_credit_note_n_orgas(user=user, name='Nerv')

        kwargs = {
            'user': user, 'related_document': credit_note,
            'unit_price': Decimal('1000.00'), 'quantity': 2,
            'discount': Decimal('10.00'),
            'discount_unit': Line.Discount.PERCENT,
            'vat_value': Vat.objects.default(),
        }
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product', **kwargs
        )
        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service', **kwargs
        )

        url = credit_note.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            credit_note = self.refresh(credit_note)

        self.assertIs(credit_note.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(credit_note)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)
        self.assertStillExists(source)
        self.assertStillExists(target)

    def test_delete_status(self):
        user = self.login_as_root_and_get()

        new_status = CreditNoteStatus.objects.first()
        status2del = CreditNoteStatus.objects.create(name='OK')

        credit_note = self.create_credit_note_n_orgas(
            user=user, name='Credit Note 001', status=status2del,
        )[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='credit_note_status',
            new_status=new_status,
            doc=credit_note,
        )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_link(self):
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

    def test_link__no_invoice(self):
        "Cannot attach credit note to invalid invoice."
        self.login_as_root()
        self.assertGET404(reverse('billing__link_to_cnotes', args=(12445,)))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_link__not_same_currency(self):
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
    def test_link__already_linked(self):
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
    def test_link__already_not_same_target(self):
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
    def test_link__regular_user(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='*')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertGET200(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    @skipIfCustomInvoice
    def test_link__credentials(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='!LINK')
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'], model=Organisation)

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertGET403(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    @skipIfCustomInvoice
    def test_link__bad_related_type(self):
        "No related to a compatible billing entity."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Foo')
        self.assertGET404(reverse('billing__link_to_cnotes', args=(orga.id,)))

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

    @skipIfCustomInvoice
    @skipIfCustomProductLine
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

    @skipIfCustomInvoice
    @skipIfCustomProductLine
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

    @skipIfCustomInvoice
    @skipIfCustomProductLine
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

    @skipIfCustomAddress
    @skipIfCustomServiceLine
    def test_clone__not_managed_emitter(self):
        "Organisation not managed."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        target.billing_address = Address.objects.create(
            name='Billing address 01',
            address='BA1 - Address', city='BA1 - City', zipcode='4242',
            owner=target,
        )
        target.save()

        credit_note = self.create_credit_note(
            user=user, name='Quote001', source=source, target=target,
            status=CreditNoteStatus.objects.filter(is_default=False)[0],
        )

        sl = ServiceLine.objects.create(
            related_item=self.create_service(user=user), user=user,
            related_document=credit_note,
        )

        address_count = Address.objects.count()

        origin_b_addr = credit_note.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        cloned = self.clone(credit_note)
        self.assertIsInstance(cloned, CreditNote)
        self.assertNotEqual(credit_note.pk, cloned.pk)
        self.assertEqual(credit_note.name,   cloned.name)
        self.assertEqual(credit_note.status, cloned.status)
        self.assertEqual('',                 cloned.number)

        self.assertEqual(source, cloned.source)
        self.assertEqual(target, cloned.target)

        # Lines are cloned
        cloned_line = self.get_alone_element(cloned.iter_all_lines())
        self.assertIsInstance(cloned_line, ServiceLine)
        self.assertNotEqual(sl.pk, cloned_line.pk)
        self.assertEqual(sl.related_item, cloned_line.related_item)
        self.assertEqual(sl.quantity,     cloned_line.quantity)
        self.assertEqual(sl.unit_price,   cloned_line.unit_price)

        # Addresses are cloned
        self.assertEqual(address_count + 2, Address.objects.count())

        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,                billing_address.owner)
        self.assertEqual(origin_b_addr.name,    billing_address.name)
        self.assertEqual(origin_b_addr.city,    billing_address.city)
        self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)

    def test_clone__managed_emitter(self):
        "Organisation is managed."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        credit_note = self.create_credit_note(
            user=user, name='My Order', source=source, target=target,
        )
        self.assertEqual('', credit_note.number)

        cloned = self.clone(credit_note)
        self.assertEqual('', cloned.number)

    # @skipIfCustomAddress
    # @skipIfCustomServiceLine
    # def test_clone__method01(self):  # DEPRECATED
    #     "Organisation not managed => number is set to '0'."
    #     user = self.login_as_root_and_get()
    #     source, target = self.create_orgas(user=user)
    #
    #     target.billing_address = Address.objects.create(
    #         name='Billing address 01',
    #         address='BA1 - Address', city='BA1 - City',
    #         owner=target,
    #     )
    #     target.save()
    #
    #     credit_note = self.create_credit_note(
    #         user=user, name='Quote001', source=source, target=target,
    #         status=CreditNoteStatus.objects.filter(is_default=False)[0],
    #     )
    #
    #     sl = ServiceLine.objects.create(
    #         related_item=self.create_service(user=user), user=user,
    #         related_document=credit_note,
    #     )
    #
    #     address_count = Address.objects.count()
    #
    #     origin_b_addr = credit_note.billing_address
    #     origin_b_addr.zipcode += ' (edited)'
    #     origin_b_addr.save()
    #
    #     cloned = self.refresh(credit_note.clone())
    #     self.assertIsInstance(cloned, CreditNote)
    #     self.assertNotEqual(credit_note.pk, cloned.pk)
    #     self.assertEqual(credit_note.name,   cloned.name)
    #     self.assertEqual(credit_note.status, cloned.status)
    #     self.assertEqual('',                 cloned.number)
    #
    #     self.assertEqual(source, cloned.source)
    #     self.assertEqual(target, cloned.target)
    #
    #     # Lines are cloned
    #     cloned_line = self.get_alone_element(cloned.iter_all_lines())
    #     self.assertIsInstance(cloned_line, ServiceLine)
    #     self.assertNotEqual(sl.pk, cloned_line.pk)
    #     self.assertEqual(sl.related_item, cloned_line.related_item)
    #     self.assertEqual(sl.quantity,     cloned_line.quantity)
    #     self.assertEqual(sl.unit_price,   cloned_line.unit_price)
    #
    #     # Addresses are cloned
    #     self.assertEqual(address_count + 2, Address.objects.count())
    #
    #     billing_address = cloned.billing_address
    #     self.assertIsInstance(billing_address, Address)
    #     self.assertEqual(cloned,                billing_address.owner)
    #     self.assertEqual(origin_b_addr.name,    billing_address.name)
    #     self.assertEqual(origin_b_addr.city,    billing_address.city)
    #     self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)
    #
    # def test_clone__method02(self):  # DEPRECATED
    #     "Organisation is managed."
    #     user = self.login_as_root_and_get()
    #
    #     source, target = self.create_orgas(user=user)
    #     self._set_managed(source)
    #
    #     credit_note = self.create_credit_note(
    #         user=user, name='My Order', source=source, target=target,
    #     )
    #     self.assertEqual('', credit_note.number)
    #
    #     cloned = credit_note.clone()
    #     self.assertEqual('', cloned.number)

    def test_brick(self):
        user = self.login_as_root_and_get()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=billing_bricks.ReceivedCreditNotesBrick, order=600,
            zone=BrickDetailviewLocation.RIGHT, model=Organisation,
        )

        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.ReceivedCreditNotesBrick,
        )
        self.assertEqual(_('Received credit notes'), self.get_brick_title(brick_node1))

        # ---
        credit_note = CreditNote.objects.create(
            user=user, name='My Quote',
            status=CreditNoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.ReceivedCreditNotesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received credit note',
            plural_title='{count} Received credit notes',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(5, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=credit_note)

    # def test_build(self):  # DEPRECATED
    #     user = self.get_root_user()
    #     status1 = CreditNoteStatus.objects.exclude(is_default=True).first()
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     tpl = TemplateBase.objects.create(
    #         user=user,
    #         ct=CreditNote,
    #         status_uuid=status1.uuid,
    #         source=create_orga(name='Source'),
    #         target=create_orga(name='Target'),
    #     )
    #
    #     credit_note1 = CreditNote().build(tpl)
    #     self.assertIsNotNone(credit_note1.pk)
    #     self.assertEqual(user,    credit_note1.user)
    #     self.assertEqual(status1, credit_note1.status)
    #
    #     # ---
    #     tpl.status_uuid = uuid4()
    #     status2 = CreditNote().build(tpl).status
    #     self.assertIsInstance(status2, CreditNoteStatus)
    #     self.assertTrue(status2.is_default)

    # TODO: complete (other views)
