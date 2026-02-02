from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.billing import number_generators
from creme.billing.forms.number_generation import (
    RegularNumberGeneratorItemEditionForm,
)
from creme.billing.models import InvoiceStatus, NumberGeneratorItem
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    TemplateBase,
    _BillingTestCase,
)


@skipIfCustomOrganisation
class NumberGenerationConfigurationEditionTestCase(_BillingTestCase):
    def test_main(self):
        user = self.login_as_standard(allowed_apps=['billing'], admin_4_apps=['billing'])
        orga = Organisation.objects.create(user=user, name='Acme')
        old_format = 'INV{counter:04}'
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': old_format, 'reset': 'never'},
        )
        self.assertIs(item.is_edition_allowed, True)

        self.assertIs(
            RegularNumberGeneratorItemEditionForm,
            number_generators.RegularNumberGenerator(item).form_class,
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
            form1 = response1.context['form']
            fields1 = form1.fields
            format_f1 = fields1['format']
            reset_f1 = fields1['reset']
            counter_f1 = fields1['counter']
            reset_choices = reset_f1.choices

        self.assertIsInstance(form1, RegularNumberGeneratorItemEditionForm)

        self.assertIn('is_edition_allowed', fields1)
        self.assertNotIn('organisation',  fields1)
        self.assertNotIn('numbered_type', fields1)

        self.assertEqual(old_format, format_f1.initial)
        self.assertEqual(1,          counter_f1.initial)
        self.assertEqual('never',    reset_f1.initial)

        self.assertInChoices(
            value='never', label=pgettext('billing-reset', 'Never'), choices=reset_choices,
        )
        self.assertInChoices(value='monthly', label=_('Monthly'), choices=reset_choices)
        self.assertInChoices(value='yearly',  label=_('Yearly'),  choices=reset_choices)

        # POST ---
        format_str = 'I-{code}-{year}-{month}-{counter:04}'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'is_edition_allowed': '',
                'format': format_str,
                'reset': 'never',
                'counter': 3,
            },
        ))
        item = self.refresh(item)
        self.assertFalse(item.is_edition_allowed)
        self.assertDictEqual(
            {'format': format_str, 'reset': 'never', 'counter': 3},
            item.data,
        )

        # POST (other reset value) ---
        self.assertNoFormError(self.client.post(
            url,
            data={
                'format': format_str,
                'reset': 'monthly',
                'counter': 4,
            },
        ))
        self.assertDictEqual(
            {'format': format_str, 'reset': 'monthly', 'counter': 4},
            self.refresh(item).data,
        )

        # GET (other initial) ---
        response2 = self.assertGET200(url)

        with self.assertNoException():
            fields2 = response2.context['form']
            reset_f2 = fields2['reset']
            counter_f2 = fields2['counter']

        self.assertEqual('monthly', reset_f2.initial)
        self.assertEqual(4,         counter_f2.initial)

    def test_permissions(self):
        self.login_as_standard(allowed_apps=['billing'])  # admin_4_apps=['billing']
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{counter:04}', 'reset': 'never'},
        )

        self.assertGET403(reverse('billing__edit_number_generator', args=(item.id,)))

    def test_errors(self):
        user = self.login_as_standard(allowed_apps=['billing'], admin_4_apps=['billing'])
        orga = Organisation.objects.create(user=user, name='Acme')
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{counter:04}', 'reset': 'never'},
        )
        url = reverse('billing__edit_number_generator', args=(item.id,))

        def post(format_str, errors, reset='never'):
            response = self.assertPOST200(
                url,
                data={
                    'is_edition_allowed': '',
                    'format': format_str,
                    'reset': reset,
                    'counter': 1,
                },
            )
            self.assertFormError(self.get_form_or_fail(response), field='format', errors=errors)

        post(
            format_str='IN-{year}-{month}',
            errors=_('You must use the variable «{counter}».'),
        )
        post(
            format_str='IN-{counter}',
            reset='yearly',
            errors=_(
                'You must use the variable «{year}» if you want to reset the counter each year.'
            ),
        )
        post(
            format_str='IN-{year}-{counter:04}',
            reset='monthly',
            errors=_(
                'You must use the variable «{month}» if you want to reset the counter each month.'
            ),
        )
        post(
            format_str='IN-{month}-{counter:03}',
            reset='monthly',
            errors=_(
                'You must use the variable «{year}» if you want to reset the counter each month.'
            ),
        )
        post(
            format_str='IN-{unknown}-{counter}',
            errors=_('The variable «{name}» is invalid.').format(name='unknown'),
        )
        post(
            format_str='IN-{}-{counter}',
            errors=_('The empty variable «{}» is forbidden.'),
        )

        # COUNTER ---
        response = self.assertPOST200(
            url,
            data={
                'is_edition_allowed': '',
                'format': 'IN-{counter}',
                'reset': 'never',
                'counter': 0,
            },
        )

        self.assertFormError(
            self.get_form_or_fail(response),
            field='counter',
            errors=_(
                'Ensure this value is greater than or equal to %(limit_value)s.'
            ) % {'limit_value': 1},
        )


@skipIfCustomOrganisation
class NumberGenerationTestCase(_BillingTestCase):
    @staticmethod
    def _build_number_generation_url(entity):
        return reverse('billing__generate_number', args=(entity.id,))

    def test_invoice__managed_emitter(self):
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
        self.assertDictEqual(
            {'format': _('INV') + '-{year}-{month}-{counter:04}', 'reset': 'never'},
            item.data,
        )

        item.data['format'] = 'IN-{counter:04}'
        item.save()

        url = self._build_number_generation_url(invoice)
        self.assertGET405(url)

        self.assertPOST200(url, follow=True)
        invoice = self.refresh(invoice)
        self.assertEqual('IN-0001', invoice.number)
        self.assertEqual(validated_status, invoice.status)
        # NB: this test can fail if run at midnight...
        self.assertEqual(date.today(), invoice.issuing_date)

        # Already generated ---
        self.assertPOST409(url, follow=True)

    def test_invoice__issuing_date(self):
        "Issuing date not overridden."
        user = self.login_as_root_and_get()

        issuing_date = date(year=2024, month=10, day=21)
        invoice, source, __target = self.create_invoice_n_orgas(
            user=user, name='Invoice001', issuing_date=issuing_date,
        )
        self.assertFalse(invoice.number)

        issuing_date = invoice.issuing_date
        self.assertTrue(issuing_date)

        self._set_managed(source)
        self.assertPOST200(self._build_number_generation_url(invoice), follow=True)
        invoice = self.refresh(invoice)
        self.assertTrue(invoice.number)
        self.assertEqual(issuing_date, invoice.issuing_date)

    def test_invoice__emitter_not_managed(self):
        "Emitter Organisation is not managed."
        user = self.login_as_root_and_get()

        issuing_date = date(year=2024, month=10, day=21)
        invoice, source, __target = self.create_invoice_n_orgas(
            user=user, name='Invoice001', issuing_date=issuing_date,
        )
        self.assertFalse(invoice.number)
        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=source))

        self.assertPOST404(self._build_number_generation_url(invoice), follow=True)

    def test_quote(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source, numbered_type=ContentType.objects.get_for_model(Quote),
        )
        self.assertDictEqual(
            {'format': _('QUO') + '-{year}-{month}-{counter:04}', 'reset': 'never'},
            item.data,
        )

        item.data['format'] = 'QU-{counter:04}'
        item.save()

        quote = self.create_quote(user=user, name='Quote001', source=source, target=target)
        number = quote.number
        self.assertEqual('QU-0001', number)  # TODO: add test in test_signals

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

    def test_sales_order(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(SalesOrder),
        )
        self.assertDictEqual(
            {'format': _('ORD') + '-{year}-{month}-{counter:04}', 'reset': 'never'},
            item.data,
        )

        item.data['format'] = 'ORD-{counter:04}'
        item.save()

        order = self.create_salesorder(user=user, name='Order001', source=source, target=target)
        self.assertEqual('ORD-0001', order.number)

        response = self.client.post(self._build_number_generation_url(order), follow=True)
        self.assertContains(
            response,
            _('The number is generated at creation for this kind of entity'),
            status_code=409,
            html=True,
        )

    def test_credit_note(self):
        "Managed Organisation."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(CreditNote),
        )
        self.assertDictEqual(
            {'format': _('CN') + '-{year}-{month}-{counter:04}', 'reset': 'never'},
            item.data,
        )

        item.data['format'] = 'CN-{counter:04}'
        item.save()

        cnote = self.create_credit_note(user=user, name='Note001', source=source, target=target)
        self.assertEqual('', cnote.number)

        self.assertPOST200(self._build_number_generation_url(cnote))
        self.assertEqual('CN-0001', self.refresh(cnote).number)

    def test_bad_type(self):
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        response = self.client.post(self._build_number_generation_url(orga), follow=True)
        self.assertContains(
            response,
            'The entity must be a billing entity',
            status_code=409,
            html=True,
        )

    def test_not_registered_type(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        tpl = TemplateBase.objects.create(
            user=user, name='Acme',
            ct=Invoice, status_uuid=InvoiceStatus.objects.first().uuid,
            source=source, target=target,
        )
        self.assertPOST404(self._build_number_generation_url(tpl))
