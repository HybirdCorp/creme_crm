from datetime import date
from functools import partial
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import number_generators
from ..bricks import NumberGeneratorItemsBrick
from ..forms.number_generation import RegularNumberGeneratorItemEditionForm
from ..models import InvoiceStatus, NumberGeneratorItem
from .base import (
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    TemplateBase,
    _BillingTestCase,
)


class NumberGenerationTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_number_generation_url(entity):
        return reverse('billing__generate_number', args=(entity.id,))

    def test_item_equal(self):
        orga1, orga2 = self.create_orgas(user=self.get_root_user())
        item = NumberGeneratorItem(
            organisation=orga1, numbered_type=Invoice, data={'key': 1},
        )
        self.assertEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Invoice, data={'key': 1},
            ),
        )
        self.assertNotEqual(item, 'different type')
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga2, numbered_type=Invoice, data={'key': 1},
            ),
        )
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Quote, data={'key': 1},
            ),
        )
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Invoice, data={'key': 2},
            ),
        )
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Invoice, data={'key': 1},
                is_edition_allowed=True,
            ),
        )

    def test_generator_classes(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')

        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=Invoice, data={'format': '{number:04}'},
            ),
            number_generators.RegularNumberGenerator.default_item(
                organisation=orga, model=Invoice,
            ),
        )
        self.assertIs(
            number_generators.RegularNumberGenerator.trigger_at_creation, True,
        )

        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=Invoice,
                data={'format': _('INV') + '{number:04}'},
            ),
            number_generators.InvoiceRegularNumberGenerator.default_item(
                organisation=orga, model=Invoice,
            ),
        )
        self.assertIs(
            number_generators.InvoiceRegularNumberGenerator.trigger_at_creation,
            False,
        )

        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=Quote,
                data={'format': _('QUO') + '{number:04}'},
            ),
            number_generators.QuoteRegularNumberGenerator.default_item(
                organisation=orga, model=Quote,
            ),
        )
        self.assertIs(
            number_generators.QuoteRegularNumberGenerator.trigger_at_creation,
            True,
        )

        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=SalesOrder,
                data={'format': _('ORD') + '{number:04}'},
            ),
            number_generators.SalesOrderRegularNumberGenerator.default_item(
                organisation=orga, model=SalesOrder,
            ),
        )
        self.assertIs(
            number_generators.SalesOrderRegularNumberGenerator.trigger_at_creation,
            True,
        )

        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=CreditNote,
                data={'format': _('CN') + '{number:04}'},
            ),
            number_generators.CreditNoteRegularNumberGenerator.default_item(
                organisation=orga, model=CreditNote,
            ),
        )
        self.assertIs(
            number_generators.CreditNoteRegularNumberGenerator.trigger_at_creation,
            True,
        )

    def test_generate__no_item(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        # item = NumberGeneratorItem.objects.create(...)

        generator = number_generators.RegularNumberGenerator(model=Invoice)
        self.assertEqual(Invoice, generator.model)
        self.assertEqual('', generator.perform(organisation=orga))

    def test_generate__prefix_n_number(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{number:04}'},
        )

        generator = number_generators.RegularNumberGenerator(model=Invoice)
        self.assertEqual(Invoice, generator.model)
        self.assertEqual('INV0001', generator.perform(organisation=orga))
        self.assertEqual('INV0002', generator.perform(organisation=orga))

        # ---
        item = self.refresh(item)
        item.data = {**item.data, 'format': 'I{number:05}'}
        item.save()
        self.assertEqual('I00003', generator.perform(organisation=orga))

    def test_generate__year_month_code(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )

        create_item = partial(NumberGeneratorItem.objects.create, organisation=orga)
        create_item(numbered_type=Invoice, data={'format': 'INV{number:04}'})
        create_item(numbered_type=Quote,   data={'format': 'QUO{year}-{month}-{code}'})

        generator = number_generators.RegularNumberGenerator(model=Quote)
        today = date.today()
        self.assertEqual(
            f'QUO{today.year}-{today.month:02}-{orga.code}',
            generator.perform(organisation=orga),
        )

    def test_generate__yearly_reset(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )
        NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Quote,
            data={
                'format': '{year}-{number}',
                'reset': 'yearly',
            },
        )

        generator = number_generators.RegularNumberGenerator(model=Quote)

        with patch('creme.billing.number_generators.datetime') as mock_datetime1:
            # Mock only datetime.date.today()
            mock_datetime1.date.today.return_value = date(year=2023, month=3, day=25)

            number1 = generator.perform(organisation=orga)

        self.assertEqual('2023-1', number1)

        # Still the same year => increment ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime2:
            mock_datetime2.date.today.return_value = date(year=2023, month=11, day=12)

            number2 = generator.perform(organisation=orga)

        self.assertEqual('2023-2', number2)

        # Year changes => reset ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime3:
            mock_datetime3.date.today.return_value = date(year=2024, month=2, day=5)

            number3 = generator.perform(organisation=orga)

        self.assertEqual('2024-1', number3)

    def test_generate__monthly_reset(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )
        NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Quote,
            data={
                'format': '{year}-{month}-{number}',
                'reset': 'monthly',
            },
        )

        generator = number_generators.RegularNumberGenerator(model=Quote)

        with patch('creme.billing.number_generators.datetime') as mock_datetime1:
            mock_datetime1.date.today.return_value = date(year=2023, month=3, day=25)

            number1 = generator.perform(organisation=orga)

        self.assertEqual('2023-03-1', number1)

        # Still the same month => increment ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime2:
            mock_datetime2.date.today.return_value = date(year=2023, month=3, day=27)

            number2 = generator.perform(organisation=orga)

        self.assertEqual('2023-03-2', number2)

        # Month changes => reset ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime3:
            mock_datetime3.date.today.return_value = date(year=2023, month=4, day=5)

            number3 = generator.perform(organisation=orga)
            number4 = generator.perform(organisation=orga)

        self.assertEqual('2023-04-1', number3)
        self.assertEqual('2023-04-2', number4)

        # Beware: year changes & not month...
        with patch('creme.billing.number_generators.datetime') as mock_datetime3:
            mock_datetime3.date.today.return_value = date(year=2024, month=4, day=5)

            number5 = generator.perform(organisation=orga)
        self.assertEqual('2024-04-1', number5)

    def test_config_brick(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Acme')
        NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{number:04}'},
        )

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('billing',))
        )
        brick_node = self.get_brick_node(
            tree=self.get_html_tree(response.content),
            brick=NumberGeneratorItemsBrick,
        )
        self.assertEqual(_('Number generation'), self.get_brick_title(brick_node))
        # TODO: complete

    def test_config_edition(self):
        user = self.login_as_standard(allowed_apps=['billing'], admin_4_apps=['billing'])
        orga = Organisation.objects.create(user=user, name='Acme')
        old_format = 'INV{number:04}'
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': old_format},
        )
        self.assertIs(item.is_edition_allowed, False)

        self.assertIs(
            RegularNumberGeneratorItemEditionForm,
            number_generators.RegularNumberGenerator(model=Invoice).form_class,
        )

        url = reverse('billing__edit_number_generator', args=(item.id,))

        # GET ---
        response1 = self.assertGET200(url)
        self.assertEqual(
            _(
                'Edit the configuration of «{object.numbered_type}» for «{object.organisation}»'
            ).format(object=item),
            response1.context.get('title'),
        )

        with self.assertNoException():
            form = response1.context['form']
            fields = form.fields
            format_f = fields['format']
            reset_f = fields['reset']
            reset_choices = reset_f.choices

        self.assertIn('is_edition_allowed', fields)
        self.assertNotIn('organisation',  fields)
        self.assertNotIn('numbered_type', fields)
        self.assertEqual(old_format, format_f.initial)
        self.assertIsInstance(form, RegularNumberGeneratorItemEditionForm)

        self.assertEqual('', reset_f.initial)
        self.assertInChoices(value='',        label=_('Never'),   choices=reset_choices)
        self.assertInChoices(value='monthly', label=_('Monthly'), choices=reset_choices)
        self.assertInChoices(value='yearly',  label=_('Yearly'), choices=reset_choices)

        # POST ---
        format_str = 'IN-{year}-{number:04}'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'is_edition_allowed': 'on',
                'format': format_str,
                'reset': '',
            },
        ))
        item = self.refresh(item)
        self.assertTrue(item.is_edition_allowed)
        self.assertDictEqual({'format': format_str, 'reset': ''}, item.data)

        # POST (other reset value ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                'format': format_str,
                'reset': 'monthly',
            },
        ))
        self.assertDictEqual(
            {'format': format_str, 'reset': 'monthly'},
            self.refresh(item).data,
        )

        # GET (other initial) ---
        response2 = self.assertGET200(url)

        with self.assertNoException():
            reset_f2 = response2.context['form'].fields['reset']

        self.assertEqual('monthly', reset_f2.initial)

    def test_config_edition__perm(self):
        self.login_as_standard(allowed_apps=['billing'])  # admin_4_apps=['billing']
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{number:04}'},
        )

        self.assertGET403(reverse('billing__edit_number_generator', args=(item.id,)))

    def test_generation_view__invoice01(self):
        "Emitter Organisation is managed."
        user = self.login_as_root_and_get()

        validated_status = self.get_object_or_fail(InvoiceStatus, is_validated=True)
        self.assertFalse(validated_status.is_default)

        invoice, source, target = self.create_invoice_n_orgas(
            user=user, name='Invoice001', issuing_date=None,
        )
        self.assertTrue(invoice.status.is_default)
        self.assertIsNone(invoice.issuing_date)

        self._set_managed(source)
        item = self.get_object_or_fail(
            NumberGeneratorItem, organisation=source, numbered_type=invoice.entity_type,
        )
        self.assertDictEqual({'format': _('INV') + '{number:04}'}, item.data)

        url = self._build_number_generation_url(invoice)
        self.assertGET405(url)

        self.assertPOST200(url, follow=True)
        invoice = self.refresh(invoice)
        self.assertEqual(_('INV') + '0001', invoice.number)
        self.assertEqual(validated_status, invoice.status)
        # NB: this test can fail if run at midnight...
        self.assertEqual(date.today(), invoice.issuing_date)

        # Already generated ---
        self.assertPOST409(url, follow=True)

    def test_generation_view__invoice02(self):
        "Emitter Organisation is not managed + issuing date not overridden."
        user = self.login_as_root_and_get()

        issuing_date = date(year=2024, month=10, day=21)
        invoice, source, __target = self.create_invoice_n_orgas(
            user=user, name='Invoice001', issuing_date=issuing_date,
        )
        self.assertFalse(invoice.number)
        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=source))

        issuing_date = invoice.issuing_date
        self.assertTrue(issuing_date)

        # TODO: number == '0' VS number == '' VS error 409
        # url = self._build_number_generation_url(invoice)
        # self.assertGET405(url, follow=True)
        # self.assertPOST200(url, follow=True)

        # invoice = self.refresh(invoice)
        # number = invoice.number
        # status = invoice.status
        # self.assertEqual('0', number)
        # self.assertEqual(validated_status, status)
        # self.assertEqual(issuing_date, invoice.issuing_date)
        #
        # # Already generated
        # self.assertPOST409(url, follow=True)
        # invoice = self.refresh(invoice)
        # self.assertEqual(number, invoice.number)
        # self.assertEqual(status, invoice.status)

    # TODO?
    # def test_generate_number__not_managed_organisation02(self):
    #     user = self.login_as_root_and_get()
    #
    #     status = InvoiceStatus.objects.create(name='OK', is_validated=True)
    #
    #     invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
    #     invoice.issuing_date = None
    #     invoice.save()
    #
    #     self.assertPOST200(self._build_gennumber_url(invoice), follow=True)
    #     invoice = self.refresh(invoice)
    #     self.assertTrue(invoice.issuing_date)
    #     self.assertEqual(status, invoice.status)
    #     # NB: this test can fail if run at midnight...
    #     self.assertEqual(date.today(), invoice.issuing_date)

    def test_generation_view__quote(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source, numbered_type=ContentType.objects.get_for_model(Quote),
        )
        self.assertDictEqual({'format': _('QUO') + '{number:04}'}, item.data)

        quote = self.create_quote(user=user, name='Quote001', source=source, target=target)
        number = quote.number
        self.assertEqual(_('QUO') + '0001', number)

        response = self.client.post(self._build_number_generation_url(quote), follow=True)
        self.assertContains(
            response,
            _('The number is generated at creation for this kind of entity'),
            status_code=409,
            html=True,
        )

        # Save again => number should not be generated again ---
        quote = self.refresh(quote)
        quote.name = 'Quote 0001'
        quote.source = source  # TODO: we should not have to do that...
        quote.save()
        self.assertEqual(number, self.refresh(quote).number)

    def test_generation_view__salesorder(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(SalesOrder),
        )
        self.assertDictEqual({'format': _('ORD') + '{number:04}'}, item.data)

        order = self.create_salesorder(user=user, name='Order001', source=source, target=target)
        self.assertEqual(_('ORD') + '0001', order.number)

        response = self.client.post(self._build_number_generation_url(order), follow=True)
        self.assertContains(
            response,
            _('The number is generated at creation for this kind of entity'),
            status_code=409,
            html=True,
        )

    def test_generation_view__creditnote(self):
        "Managed Organisation."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(CreditNote),
        )
        self.assertDictEqual({'format': _('CN') + '{number:04}'}, item.data)

        cnote = self.create_credit_note(user=user, name='Note001', source=source, target=target)
        self.assertEqual(_('CN') + '0001', cnote.number)

        response = self.client.post(self._build_number_generation_url(cnote), follow=True)
        self.assertContains(
            response,
            _('The number is generated at creation for this kind of entity'),
            status_code=409,
            html=True,
        )

    def test_generation_view__bad_type(self):
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        response = self.client.post(self._build_number_generation_url(orga), follow=True)
        self.assertContains(
            response,
            'The entity must be a billing entity',
            status_code=409,
            html=True,
        )

    def test_generation_view__not_registered_type(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        tpl = TemplateBase.objects.create(
            user=user, name='Acme',
            ct=Invoice, status_uuid=InvoiceStatus.objects.first().uuid,
            source=source, target=target,
        )

        response = self.client.post(self._build_number_generation_url(tpl), follow=True)
        self.assertContains(
            response,
            _('This kind of entity cannot not generate a number.'),
            status_code=409,
            html=True,
        )
