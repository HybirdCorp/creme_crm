from datetime import date
from decimal import Decimal
from functools import partial

from django.template import Context, Template
from django.urls import reverse
from django.utils.translation import gettext as _

# from creme.creme_core.auth import EntityCredentials
from creme.creme_core.gui.view_tag import ViewTag
# from creme.creme_core.models import SetCredentials
from creme.creme_core.models import (
    BrickDetailviewLocation,
    Currency,
    FakeOrganisation,
    FieldsConfig,
    Relation,
    Vat,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from ..bricks import CreditNotesBrick, ReceivedCreditNotesBrick
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
    TemplateBase,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
)


@skipIfCustomOrganisation
@skipIfCustomCreditNote
class CreditNoteTestCase(BrickTestCaseMixin, _BillingTestCase):
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

    def test_status(self):
        statuses = [*CreditNoteStatus.objects.all()]
        self.assertEqual(4, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertEqual(1, default_status.pk)

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

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_createview01(self):
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

        # ---
        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=CreditNotesBrick,
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
            url=self._build_editcomment_url(credit_note),
            action_type='edit',
        )
        # TODO: complete (hidden fields, no view permission)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_createview02(self):
        "Credit note total > document billing total where the credit note is applied"
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
    def test_createview03(self):
        "Credit note in a negative Invoice -> a bigger negative Invoice"
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

        credit_note.restore()
        self.assertFalse(self.refresh(credit_note).is_deleted)
        self.assertListEqual([credit_note], self.refresh(invoice).get_credit_notes())
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)

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
    def test_addrelated_view(self):
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

    def test_addrelated_view_no_invoice(self):
        "Cannot attach credit note to invalid invoice."
        self.login_as_root()
        self.assertGET404(reverse('billing__link_to_cnotes', args=(12445,)))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_addrelated_view_not_same_currency(self):
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
            response.context['form'],
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
    def test_addrelated_view_already_linked(self):
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
            response.context['form'],
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
    def test_addrelated_view_already_not_same_target(self):
        "Cannot attach credit note in US Dollar to invoice in Euro."
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
            response.context['form'],
            field='credit_notes',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': credit_note},
        )

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 300)

    @skipIfCustomInvoice
    def test_addrelated_view_notsuperuser(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_ALL,
        # )
        self.add_credentials(user.role, all='*')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertGET200(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    @skipIfCustomInvoice
    def test_addrelated_view_linkcredentials(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Invoice],
        )
        # create_sc = partial(
        #     SetCredentials.objects.create,
        #     role=user.role, set_type=SetCredentials.ESET_ALL,
        # )
        # create_sc(
        #     value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
        #     ctype=Organisation,
        # )
        # create_sc(
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         # | EntityCredentials.LINK   # <==
        #         | EntityCredentials.UNLINK
        #     ),
        # )
        self.add_credentials(user.role, all='!LINK')
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'], model=Organisation)

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]
        self.assertGET403(reverse('billing__link_to_cnotes', args=(invoice.id,)))

    def test_editview(self):
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

        self.assertRelationCount(1, cnote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, cnote, REL_SUB_BILL_RECEIVED, target)

    @skipIfCustomInvoice
    def test_addrelated_view_badrelated(self):
        "No related to a compatible billing entity"
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Foo')
        self.assertGET404(reverse('billing__link_to_cnotes', args=(orga.id,)))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_deleterelated_view(self):
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

        self.assertPOST404(self._build_deleterelated_url(credit_note, invoice), follow=True)

        self.assertFalse(
            Relation.objects.filter(object_entity=invoice, subject_entity=credit_note),
        )
        self.assertInvoiceTotalToPay(invoice, 100)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_deleterelated_view_not_allowed(self):
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
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=CreditNote,
            descriptions=[('issuing_date', {FieldsConfig.HIDDEN: True})],
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]

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
        user = self.login_as_root_and_get()
        FieldsConfig.objects.create(
            content_type=CreditNote,
            descriptions=[('comment', {FieldsConfig.HIDDEN: True})],
        )

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        self.assertGET409(self._build_editcomment_url(credit_note))

    def test_editcomment03(self):
        "Not super-user."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[CreditNote],
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
        #     set_type=SetCredentials.ESET_ALL,
        # )
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        self.assertGET200(self._build_editcomment_url(credit_note))

    def test_editcomment04(self):
        "CHANGE permission is needed."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[CreditNote],
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=EntityCredentials.VIEW | EntityCredentials.LINK,  # Not CHANGE
        #     set_type=SetCredentials.ESET_ALL,
        # )
        self.add_credentials(user.role, all=['VIEW', 'LINK'])  # Not 'CHANGE'

        credit_note = self.create_credit_note_n_orgas(user=user, name='Credit Note 001')[0]
        self.assertGET403(self._build_editcomment_url(credit_note))

    def test_brick(self):
        user = self.login_as_root_and_get()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=ReceivedCreditNotesBrick, order=600,
            zone=BrickDetailviewLocation.RIGHT, model=Organisation,
        )

        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=ReceivedCreditNotesBrick,
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
            brick=ReceivedCreditNotesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received credit note',
            plural_title='{count} Received credit notes',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(4, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=credit_note)

    def test_build(self):
        user = self.get_root_user()
        status = CreditNoteStatus.objects.exclude(is_default=True).first()
        create_orga = partial(Organisation.objects.create, user=user)
        tpl = TemplateBase.objects.create(
            user=user,
            ct=CreditNote,
            status_id=status.id,
            source=create_orga(name='Source'),
            target=create_orga(name='Target'),
        )

        credit_note1 = CreditNote().build(tpl)
        self.assertIsNotNone(credit_note1.pk)
        self.assertEqual(user,   credit_note1.user)
        self.assertEqual(status, credit_note1.status)

        # ---
        tpl.status_id = self.UNUSED_PK
        status2 = CreditNote().build(tpl).status
        self.assertIsInstance(status2, CreditNoteStatus)
        self.assertTrue(status2.is_default)

    # TODO: complete (other views)
