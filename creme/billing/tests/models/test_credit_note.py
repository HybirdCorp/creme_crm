from decimal import Decimal
from functools import partial

from django.template import Context, Template

from creme.billing.constants import (
    REL_SUB_CREDIT_NOTE_APPLIED,
    UUID_CNOTE_STATUS_DRAFT,
)
from creme.billing.models import CreditNoteStatus, Line
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import Relation, Vat
from creme.persons.tests.base import skipIfCustomAddress

from ..base import (
    Address,
    CreditNote,
    ProductLine,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomServiceLine,
)


class CreditNoteStatusTestCase(_BillingTestCase):
    def test_create(self):
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

    def test_render(self):
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


@skipIfCustomCreditNote
class CreditNoteTestCase(_BillingTestCase):
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

        rel = Relation.objects.create(
            object_entity=invoice, subject_entity=credit_note,
            type_id=REL_SUB_CREDIT_NOTE_APPLIED, user=user,
        )
        self.assertEqual(Decimal('40'), self.refresh(invoice).total_no_vat)
        self.assertEqual([credit_note], self.refresh(invoice).get_credit_notes())

        rel.delete()
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
