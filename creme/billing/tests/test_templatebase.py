from datetime import date, timedelta
from functools import partial
from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    Relation,
    RelationType,
)
from creme.persons.tests.base import skipIfCustomOrganisation

from ..models import (
    AdditionalInformation,
    CreditNoteStatus,
    InvoiceStatus,
    NumberGeneratorItem,
    PaymentTerms,
    QuoteStatus,
    SalesOrderStatus,
)
from .base import (
    Address,
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    ServiceLine,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomQuote,
    skipIfCustomSalesOrder,
    skipIfCustomTemplateBase,
)


@skipIfCustomOrganisation
@skipIfCustomTemplateBase
class TemplateBaseTestCase(_BillingTestCase):
    STATUS_KEY = 'cform_extra-billing_template_status'

    def setUp(self):
        super().setUp()
        self.user = user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        self.source = create_orga(name='Source')
        self.target = create_orga(name='Target')

    def _create_templatebase(self, model, status_uuid, name=None, comment='', **kwargs):
        return TemplateBase.objects.create(
            user=self.user,
            ct=model,
            name=name or f'{model._meta.verbose_name} template',
            status_uuid=status_uuid,
            comment=comment,
            source=self.source,
            target=self.target,
            **kwargs
        )

    def test_detailview(self):
        invoice_status = InvoiceStatus.objects.filter(is_default=False).first()
        tpl = self._create_templatebase(Invoice, status_uuid=invoice_status.uuid)
        response = self.assertGET200(tpl.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_template.html')

    def test_status_function_field(self):
        status = InvoiceStatus.objects.filter(is_default=False).first()
        tpl = self._create_templatebase(Invoice, status_uuid=status.uuid)

        with self.assertNoException():
            funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        self.assertIsNotNone(funf)

        # ---
        with self.assertNumQueries(1):
            render1 = funf(tpl, self.user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(str(status), render1)

        # ---
        with self.assertNumQueries(0):
            render2 = funf(tpl, self.user).render(ViewTag.HTML_LIST)

        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            render2,
        )

        # ---
        with self.assertNumQueries(0):
            render3 = funf(tpl, self.user).render(ViewTag.HTML_LIST)

        self.assertEqual(render2, render3)

    def test_status_function_field__populate(self):
        user = self.user

        status1, status2 = InvoiceStatus.objects.filter(is_default=False)[:2]
        tpl1 = self._create_templatebase(Invoice, status_uuid=status1.uuid)
        tpl2 = self._create_templatebase(Invoice, status_uuid=status2.uuid)

        funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        with self.assertNumQueries(1):
            funf.populate_entities(entities=[tpl1, tpl2], user=user)

        with self.assertNumQueries(0):
            render1 = funf(tpl1, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status1), render1)

        with self.assertNumQueries(0):
            render2 = funf(tpl2, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status2), render2)

        # Status already retrieved
        tpl3 = self._create_templatebase(Invoice, status_uuid=status2.uuid)
        with self.assertNumQueries(0):
            funf.populate_entities(entities=[tpl1, tpl2, tpl3], user=user)

        with self.assertNumQueries(0):
            render3 = funf(tpl3, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status2), render3)

    def test_status_function_field__populate_several_models(self):
        user = self.user

        status1 = InvoiceStatus.objects.filter(is_default=False).first()
        status2 = QuoteStatus.objects.filter(is_default=False).first()
        tpl1 = self._create_templatebase(Invoice, status_uuid=status1.uuid)
        tpl2 = self._create_templatebase(Quote, status_uuid=status2.uuid)

        funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        with self.assertNumQueries(2):
            funf.populate_entities(entities=[tpl1, tpl2], user=user)

        with self.assertNumQueries(0):
            render1 = funf(tpl1, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status1), render1)

        with self.assertNumQueries(0):
            render2 = funf(tpl2, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status2), render2)

    @skipIfCustomInvoice
    def test_create_invoice(self):
        target_orga = self.target
        target_orga.billing_address = Address.objects.create(
            name='Billing address 01', address='BA1 - Address',
            po_box='BA1 - PO box', zipcode='BA1 - Zip code',
            city='BA1 - City', department='BA1 - Department',
            state='BA1 - State', country='BA1 - Country',
            owner=target_orga,
        )
        target_orga.save()

        invoice_status = InvoiceStatus.objects.filter(is_default=False).first()
        comment = '*Insert a comment here*'
        tpl = self._create_templatebase(
            Invoice,
            status_uuid=invoice_status.uuid,
            comment=comment,
            additional_info=AdditionalInformation.objects.all()[0],
            payment_terms=PaymentTerms.objects.all()[0],
        )
        self.assertEqual('', tpl.number)

        origin_b_addr = tpl.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        sl = ServiceLine.objects.create(
            related_item=self.create_service(user=self.user),
            user=self.user, related_document=tpl,
        )

        address_count = Address.objects.count()

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertIsInstance(invoice, Invoice)
        self.assertEqual(comment, invoice.comment)
        self.assertEqual(invoice_status, invoice.status)
        self.assertEqual(tpl.additional_info, invoice.additional_info)
        self.assertEqual(tpl.payment_terms,   invoice.payment_terms)
        self.assertEqual(self.source, invoice.source)
        self.assertEqual(self.target, invoice.target)

        self.assertEqual('', invoice.number)
        self.assertEqual(date.today(), invoice.issuing_date)
        self.assertEqual(
            invoice.issuing_date + timedelta(days=30),
            invoice.expiration_date,
        )

        # Lines are cloned
        cloned_lines = [*invoice.iter_all_lines()]
        self.assertEqual(1, len(cloned_lines))
        self.assertNotEqual([sl], cloned_lines)

        # Addresses are cloned
        self.assertEqual(address_count + 2, Address.objects.count())
        billing_address = invoice.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(invoice,               billing_address.owner)
        self.assertEqual(origin_b_addr.name,    billing_address.name)
        self.assertEqual(origin_b_addr.city,    billing_address.city)
        self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)

    @skipIfCustomInvoice
    def test_create_invoice__bad_status_id(self):
        tpl = self._create_templatebase(Invoice, status_uuid=uuid4())

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertTrue(invoice.status.is_default)

    @skipIfCustomInvoice
    def test_create_invoice__managed_emitter(self):
        "Source is managed."
        self._set_managed(self.source)
        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=self.source,
            numbered_type=ContentType.objects.get_for_model(Invoice),
        )
        item.data['format'] = 'INV-{counter:04}'
        item.save()

        invoice_status = InvoiceStatus.objects.filter(is_default=False).first()

        tpl = self._create_templatebase(Invoice, status_uuid=invoice_status.uuid)
        self.assertEqual('', tpl.number)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertIsInstance(invoice, Invoice)
        self.assertEqual('INV-0001', invoice.number)

    @skipIfCustomInvoice
    def test_create_invoice__not_managed_emitter(self):
        "Source is not managed + fallback number."
        invoice_status = InvoiceStatus.objects.filter(is_default=False).first()
        number = 'INV132'
        tpl = self._create_templatebase(Invoice, status_uuid=invoice_status.uuid, number=number)

        with self.assertNoException():
            invoice = tpl.create_entity()

        self.assertEqual(number, invoice.number)

    @skipIfCustomQuote
    def test_create_quote(self):
        "Quote + Properties + Relations."
        quote_status = QuoteStatus.objects.filter(is_default=False).first()
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(
            Quote, status_uuid=quote_status.uuid, comment=comment,
        )

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='OK')
        ptype2 = create_ptype(text='KO')
        ptype2.set_subject_ctypes(TemplateBase)

        create_prop = partial(CremeProperty.objects.create, creme_entity=tpl)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        rtype1 = RelationType.objects.builder(
            id='test-subject_ok', predicate='OK',
        ).symmetric(id='test-object_ok', predicate='symmetric OK').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_ko', predicate='KO', models=[TemplateBase],
        ).symmetric(id='test-object_ko', predicate='symmetric KO').get_or_create()[0]

        user = self.get_root_user()
        related = Organisation.objects.create(user=user, name='Acme')

        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=tpl, object_entity=related,
        )
        create_rel(type=rtype1)
        create_rel(type=rtype2)

        with self.assertNoException():
            quote = tpl.create_entity()

        self.assertIsInstance(quote, Quote)
        self.assertEqual(comment, quote.comment)
        self.assertEqual(quote_status, quote.status)

        self.assertListEqual(
            [ptype1],
            [p.type for p in quote.properties.all()],
        )
        self.assertListEqual(
            [(rtype1.id, related.id)],
            [
                *quote.relations
                      .filter(type__in=[rtype1, rtype2])
                      .values_list('type', 'object_entity'),
            ],
        )

    @skipIfCustomQuote
    def test_create_quote__bad_uuid(self):
        "Bad status uuid."
        uid = uuid4()
        self.assertFalse(QuoteStatus.objects.filter(uuid=uid))

        default_status = self.get_object_or_fail(QuoteStatus, is_default=True)
        tpl = self._create_templatebase(Quote, status_uuid=uid)

        with self.assertLogs(level='WARNING') as logs_manager:
            with self.assertNoException():
                quote = tpl.create_entity()

        self.assertEqual(default_status, quote.status)

        self.assertIn(
            f'Invalid status UUID in TemplateBase(id={tpl.id})',
            logs_manager.output[0],
        )

    @skipIfCustomQuote
    def test_create_quote__no_default_status_available(self):
        QuoteStatus.objects.filter(is_default=True).delete()
        status_ids = {*QuoteStatus.objects.values_list('id', flat=True)}
        uid = uuid4()

        tpl = self._create_templatebase(Quote, status_uuid=uid)

        with self.assertLogs(level='WARNING') as logs_manager:
            with self.assertNoException():
                quote = tpl.create_entity()

        status = quote.status
        self.assertIsNotNone(status)
        self.assertIn(status.id, status_ids)

        self.assertIn(
            "No default instance found for "
            "<class 'creme.billing.models.other_models.QuoteStatus'>",
            logs_manager.output[0],
        )
        self.assertIn(
            f'Invalid status UUID in TemplateBase(id={tpl.id})',
            logs_manager.output[1],
        )

    @skipIfCustomQuote
    def test_create_quote__no_status_available(self):
        QuoteStatus.objects.all().delete()
        uid = uuid4()

        tpl = self._create_templatebase(Quote, status_uuid=uid)

        with self.assertLogs(level='WARNING') as logs_manager:
            with self.assertNoException():
                quote = tpl.create_entity()

        status = quote.status
        self.assertIsNotNone(status)
        self.assertEqual(_('N/A'), status.name)

        self.assertIn(
            "No default instance found for "
            "<class 'creme.billing.models.other_models.QuoteStatus'>",
            logs_manager.output[0],
        )
        self.assertIn(
            f'Invalid status UUID in TemplateBase(id={tpl.id})',
            logs_manager.output[1],
        )
        self.assertIn(
            'no Quote Status available, so we create one',
            logs_manager.output[2],
        )

    @skipIfCustomQuote
    def test_create_quote__managed_source(self):
        "Source is managed."
        self._set_managed(self.source)
        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=self.source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        item.data['format'] = 'QU-{counter:04}'
        item.save()

        quote_status = QuoteStatus.objects.filter(is_default=False).first()
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(Quote, status_uuid=quote_status.uuid, comment=comment)

        with self.assertNoException():
            quote = tpl.create_entity()

        self.assertIsInstance(quote, Quote)
        self.assertEqual(comment, quote.comment)
        self.assertEqual(quote_status, quote.status)
        self.assertEqual('QU-0001', quote.number)

    @skipIfCustomSalesOrder
    def test_create_order(self):
        order_status = SalesOrderStatus.objects.filter(is_default=False).first()
        tpl = self._create_templatebase(SalesOrder, status_uuid=order_status.uuid)

        with self.assertNoException():
            order = tpl.create_entity()

        self.assertIsInstance(order, SalesOrder)
        self.assertEqual(order_status, order.status)

    @skipIfCustomSalesOrder
    def test_create_order__bad_status_id(self):
        tpl = self._create_templatebase(SalesOrder, status_uuid=uuid4())

        with self.assertNoException():
            order = tpl.create_entity()

        self.assertEqual(SalesOrderStatus.objects.default().id, order.status_id)

    @skipIfCustomCreditNote
    def test_create_cnote(self):
        cnote_status = CreditNoteStatus.objects.filter(is_default=False).first()
        comment = '*Insert an nice comment here*'
        tpl = self._create_templatebase(
            CreditNote, status_uuid=cnote_status.uuid, comment=comment,
        )

        with self.assertNoException():
            cnote = tpl.create_entity()

        self.assertIsInstance(cnote, CreditNote)
        self.assertEqual(comment, cnote.comment)
        self.assertEqual(cnote_status, cnote.status)

    def test_create_error(self):
        tpl = self._create_templatebase(Organisation, status_uuid=uuid4())

        with self.assertRaises(ValueError) as cm:
            tpl.create_entity()

        self.assertEqual(
            'Invalid target model; please contact your administrator.',
            str(cm.exception),
        )

    def test_editview(self):
        user = self.user

        invoice_status1, invoice_status2 = InvoiceStatus.objects.filter(
            is_default=False,
        ).order_by('-id')[:2]

        name = 'My template'
        tpl = self._create_templatebase(Invoice, status_uuid=invoice_status1.uuid, name=name)

        url = tpl.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            formfields = response1.context['form'].fields
            source_f = formfields[self.SOURCE_KEY]
            target_f = formfields[self.TARGET_KEY]
            status_f = formfields[self.STATUS_KEY]
            number_f = formfields['number']

        self.assertEqual(self.source, source_f.initial)
        self.assertEqual(self.target, target_f.initial)
        self.assertEqual(invoice_status1.id, status_f.initial)
        self.assertEqual(
            _(
                'If a number is given, it will be only used as fallback value '
                'when generating a number in the final recurring entities.'
            ),
            number_f.help_text,
        )

        # ---
        name += ' (edited)'

        create_orga = partial(Organisation.objects.create, user=self.user)
        source2 = create_orga(name='Source Orga 2')
        target2 = create_orga(name='Target Orga 2')

        response2 = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2020, 10, 31),
                'expiration_date': self.formfield_value_date(2020, 11, 30),
                self.STATUS_KEY:    invoice_status2.id,
                'currency':        tpl.currency_id,
                'discount':        '0',

                self.SOURCE_KEY: source2.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target2),
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, tpl.get_absolute_url())

        tpl = self.refresh(tpl)
        self.assertEqual(name, tpl.name)
        self.assertEqual(date(year=2020, month=11, day=30), tpl.expiration_date)
        self.assertIsNone(tpl.payment_info)
        self.assertUUIDEqual(invoice_status2.uuid, tpl.status_uuid)

        self.assertEqual(source2, tpl.source)
        self.assertEqual(target2, tpl.target)

    def test_listview(self):
        invoice_status = InvoiceStatus.objects.first()
        quote_status   = QuoteStatus.objects.first()

        tpl1 = self._create_templatebase(
            Invoice, status_uuid=invoice_status.uuid, name='Invoice template',
        )
        tpl2 = self._create_templatebase(
            Quote, status_uuid=quote_status.uuid, name='Quote template',
        )

        response = self.assertGET200(TemplateBase.get_lv_absolute_url())

        with self.assertNoException():
            quotes_page = response.context['page_obj']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertCountEqual([tpl1, tpl2], quotes_page.paginator.object_list)

    def test_delete_invoice_status(self):
        new_status, other_status = InvoiceStatus.objects.all()[:2]
        status2del = InvoiceStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(Invoice, status_uuid=status2del.uuid)
        tpl2 = self._create_templatebase(Invoice, status_uuid=other_status.uuid)
        tpl3 = self._create_templatebase(Quote,   status_uuid=status2del.uuid)

        invoice = self.create_invoice_n_orgas(user=self.user, name='Nerv')[0]
        invoice.status = status2del
        invoice.save()

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='invoice_status',
            new_status=new_status,
            doc=invoice,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertUUIDEqual(new_status.uuid, tpl1.status_uuid)

        tpl2 = self.refresh(tpl2)
        self.assertUUIDEqual(other_status.uuid, tpl2.status_uuid)

        tpl3 = self.refresh(tpl3)
        self.assertUUIDEqual(status2del.uuid, tpl3.status_uuid)

    def test_delete_quote_status(self):
        new_status, other_status = QuoteStatus.objects.all()[:2]
        status2del = QuoteStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(Quote,   status_uuid=status2del.uuid)
        tpl2 = self._create_templatebase(Quote,   status_uuid=other_status.uuid)
        tpl3 = self._create_templatebase(Invoice, status_uuid=status2del.uuid)

        quote = self.create_quote_n_orgas(user=self.user, name='Nerv', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='quote_status',
            new_status=new_status,
            doc=quote,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertUUIDEqual(new_status.uuid, tpl1.status_uuid)

        tpl2 = self.refresh(tpl2)
        self.assertUUIDEqual(other_status.uuid, tpl2.status_uuid)

        tpl3 = self.refresh(tpl3)
        self.assertUUIDEqual(status2del.uuid, tpl3.status_uuid)

    def test_delete_salesorder_status(self):
        new_status, other_status = SalesOrderStatus.objects.all()[:2]
        status2del = SalesOrderStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(SalesOrder, status_uuid=status2del.uuid)
        tpl2 = self._create_templatebase(SalesOrder, status_uuid=other_status.uuid)
        tpl3 = self._create_templatebase(Invoice,    status_uuid=status2del.uuid)

        order = self.create_salesorder_n_orgas(user=self.user, name='Order', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='sales_order_status',
            new_status=new_status,
            doc=order,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertUUIDEqual(new_status.uuid, tpl1.status_uuid)

        tpl2 = self.refresh(tpl2)
        self.assertUUIDEqual(other_status.uuid, tpl2.status_uuid)

        tpl3 = self.refresh(tpl3)
        self.assertUUIDEqual(status2del.uuid, tpl3.status_uuid)

    def test_delete_creditnote_status(self):
        new_status, other_status = CreditNoteStatus.objects.all()[:2]
        status2del = CreditNoteStatus.objects.create(name='OK')

        tpl1 = self._create_templatebase(CreditNote, status_uuid=status2del.uuid)
        tpl2 = self._create_templatebase(CreditNote, status_uuid=other_status.uuid)
        tpl3 = self._create_templatebase(Invoice,    status_uuid=status2del.uuid)

        credit_note = self.create_credit_note_n_orgas(
            user=self.user, name='Credit Note', status=status2del,
        )[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='credit_note_status',
            new_status=new_status,
            doc=credit_note,
        )

        tpl1 = self.assertStillExists(tpl1)
        self.assertUUIDEqual(new_status.uuid, tpl1.status_uuid)

        tpl2 = self.refresh(tpl2)
        self.assertUUIDEqual(other_status.uuid, tpl2.status_uuid)

        tpl3 = self.refresh(tpl3)
        self.assertUUIDEqual(status2del.uuid, tpl3.status_uuid)

    # TODO: test form
