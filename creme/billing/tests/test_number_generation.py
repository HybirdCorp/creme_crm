from datetime import date
from functools import partial
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.forms import CharField
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui import actions
from creme.creme_core.models import Currency
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from .. import number_generators
from ..actions import (
    GenerateCreditNoteNumberAction,
    GenerateInvoiceNumberAction,
)
from ..bricks import NumberGeneratorItemsBrick
from ..core.number_generation import NumberGenerator, NumberGeneratorRegistry
from ..forms.number_generation import RegularNumberGeneratorItemEditionForm
from ..models import InvoiceStatus, NumberGeneratorItem, QuoteStatus
from .base import (
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    TemplateBase,
    _BillingTestCase,
)


@skipIfCustomOrganisation
class NumberGenerationTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_number_generation_url(entity):
        return reverse('billing__generate_number', args=(entity.id,))

    def test_registry(self):
        class TestInvoiceNumberGenerator(NumberGenerator):
            pass

        class TestQuoteNumberGenerator(NumberGenerator):
            pass

        orga = Organisation(user=self.get_root_user(), name='Acme')
        item1 = NumberGeneratorItem(organisation=orga, numbered_type=Invoice)
        item2 = NumberGeneratorItem(organisation=orga, numbered_type=Quote)

        registry = NumberGeneratorRegistry()
        self.assertIsNone(registry.get(item1))
        self.assertFalse([*registry.registered_items()])

        with self.assertRaises(ConflictError) as cm:
            registry[item1]  # NOQA
        self.assertEqual(
            _('This kind of entity cannot not generate a number.'),
            str(cm.exception),
        )

        # ---
        registry.register(
            model=Invoice, generator_cls=TestInvoiceNumberGenerator,
        ).register(
            model=Quote, generator_cls=TestQuoteNumberGenerator,
        )
        self.assertIsInstance(registry.get(item1), TestInvoiceNumberGenerator)
        self.assertIsInstance(registry.get(item2), TestQuoteNumberGenerator)

        self.assertIsInstance(registry[item1], TestInvoiceNumberGenerator)
        self.assertIsInstance(registry[item2], TestQuoteNumberGenerator)

        self.assertCountEqual(
            [
                (Invoice, TestInvoiceNumberGenerator),
                (Quote,   TestQuoteNumberGenerator),
            ],
            [*registry.registered_items()],
        )

        # ---
        with self.assertRaises(NumberGeneratorRegistry.RegistrationError):
            registry.register(model=Invoice, generator_cls=TestQuoteNumberGenerator)

        # ---
        registry.unregister(model=Invoice)
        self.assertIsNone(registry.get(item1))

        # ---
        with self.assertRaises(NumberGeneratorRegistry.UnRegistrationError):
            registry.unregister(model=Invoice)

    def test_manager__get_for_model(self):
        user = self.get_root_user()
        orga1, orga2 = self.create_orgas(user=user)

        create_item = partial(NumberGeneratorItem.objects.create, numbered_type=Invoice)
        item1 = create_item(organisation=orga1, data={'key': 1})
        item2 = create_item(organisation=orga2, data={'key': 2})
        item3 = create_item(organisation=orga2, data={'key': 3}, numbered_type=Quote)

        with self.assertNumQueries(1):
            items1 = NumberGeneratorItem.objects.get_for_model(Invoice)

        with self.assertNumQueries(0):
            retr_item1 = items1.get_for_organisation(orga1)

        self.assertIsInstance(retr_item1, NumberGeneratorItem)
        self.assertEqual(item1.id, retr_item1.id)

        self.assertEqual(item2.id, items1.get_for_organisation(orga2).id)

        # Cache ---
        with self.assertNumQueries(0):
            items2 = NumberGeneratorItem.objects.get_for_model(Invoice)
        self.assertIs(items2, items1)

        with self.assertNumQueries(0):
            itered = [*NumberGeneratorItem.objects.get_for_model(Invoice)]
        self.assertIn(item1, itered)
        self.assertIn(item2, itered)
        self.assertNotIn(item3, itered)

        # No item ---
        orga3 = Organisation.objects.create(user=user, name='Acme')
        self.assertIsNone(items2.get_for_organisation(orga3))

    def test_manager__get_for_instance(self):
        user = self.get_root_user()
        orga1, orga2 = self.create_orgas(user=user)

        item = NumberGeneratorItem.objects.create(
            organisation=orga1, numbered_type=Invoice,
        )

        invoice1 = Invoice.objects.create(
            user=user, name='Invoice001', source=orga1, target=orga2,
        )

        with self.assertNumQueries(1):
            retr_item1 = NumberGeneratorItem.objects.get_for_instance(invoice1)

        self.assertIsInstance(retr_item1, NumberGeneratorItem)
        self.assertEqual(item.id, retr_item1.id)

        # Cache ---
        with self.assertNumQueries(0):
            NumberGeneratorItem.objects.get_for_instance(invoice1)

        # No item ---
        invoice2 = Invoice.objects.create(
            user=user, name='Invoice001', source=orga2, target=orga1,
        )

        with self.assertNumQueries(0):
            retr_item2 = NumberGeneratorItem.objects.get_for_instance(invoice2)
        self.assertIsNone(retr_item2)

    def test_item_equal(self):
        orga1, orga2 = self.create_orgas(user=self.get_root_user())
        item = NumberGeneratorItem(
            organisation=orga1, numbered_type=Invoice, data={'key': 1},
            is_edition_allowed=True,
        )
        self.assertEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Invoice, data={'key': 1},
                is_edition_allowed=True,
            ),
        )
        self.assertNotEqual(item, 'different type')
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga2, numbered_type=Invoice, data={'key': 1},
                is_edition_allowed=True,
            ),
        )
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Quote, data={'key': 1},
                is_edition_allowed=True,
            ),
        )
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Invoice, data={'key': 2},
                is_edition_allowed=True,
            ),
        )
        self.assertNotEqual(
            item,
            NumberGeneratorItem(
                organisation=orga1, numbered_type=Invoice, data={'key': 1},
                is_edition_allowed=False,
            ),
        )

    def test_generator_classes(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')

        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=Invoice,
                data={
                    'format': _('INV') + '-{year}-{month}-{counter:04}', 'reset': 'never',
                },
            ),
            number_generators.InvoiceRegularNumberGenerator.create_default_item(
                organisation=orga, model=Invoice,
            ),
        )
        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=Quote,
                data={
                    'format': _('QUO') + '-{year}-{month}-{counter:04}', 'reset': 'never'
                },
            ),
            number_generators.QuoteRegularNumberGenerator.create_default_item(
                organisation=orga, model=Quote,
            ),
        )
        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=SalesOrder,
                data={
                    'format': _('ORD') + '-{year}-{month}-{counter:04}', 'reset': 'never',
                },
            ),
            number_generators.SalesOrderRegularNumberGenerator.create_default_item(
                organisation=orga, model=SalesOrder,
            ),
        )
        self.assertEqual(
            NumberGeneratorItem(
                organisation=orga, numbered_type=CreditNote,
                data={
                    'format': _('CN') + '-{year}-{month}-{counter:04}', 'reset': 'never',
                },
            ),
            number_generators.CreditNoteRegularNumberGenerator.create_default_item(
                organisation=orga, model=CreditNote,
            ),
        )

    def test_generator_perform__check_permissions(self):
        user = self.login_as_standard(allowed_apps=['billing'])
        self.add_credentials(user.role, own=['VIEW', 'CHANGE'], all=['VIEW'])

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        invoice = Invoice.objects.create(
            user=user, name='Inv001', source=source, target=target,
        )
        item = self.get_object_or_fail(
            NumberGeneratorItem, numbered_type=invoice.entity_type, organisation=source,
        )

        generator = number_generators.RegularNumberGenerator(item)
        with self.assertNoException():
            generator.check_permissions(user=user, entity=invoice)

        # ---
        invoice.number = 'INV-001'
        with self.assertRaises(ConflictError) as cm1:
            generator.check_permissions(user=user, entity=invoice)
        self.assertEqual(_('This entity has already a number'), str(cm1.exception))

        # ---
        invoice.number = ''
        invoice.user = self.get_root_user()
        invoice.save()

        with self.assertRaises(PermissionDenied) as cm2:
            generator.check_permissions(user=user, entity=self.refresh(invoice))
        self.assertEqual(
            _('You are not allowed to edit this entity: {}').format(str(invoice)),
            str(cm2.exception),
        )

    def test_generator_perform__prefix_n_number(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{counter:04}'},
        )

        generator = number_generators.RegularNumberGenerator(item)
        self.assertEqual('INV0001', generator.perform())
        self.assertEqual('INV0002', generator.perform())

        # ---
        item = self.refresh(item)
        item.data = {**item.data, 'format': 'I{counter:05}'}
        item.save()
        self.assertEqual('I00003', number_generators.RegularNumberGenerator(item).perform())

    def test_generator_perform__year_month_code(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )

        item = NumberGeneratorItem.objects.create(
            numbered_type=Quote, organisation=orga, data={'format': 'QUO{year}-{month}-{code}'},
        )

        generator = number_generators.RegularNumberGenerator(item=item)
        today = date.today()
        self.assertEqual(
            f'QUO{today.year}-{today.month:02}-{orga.code}',
            generator.perform(),
        )

    def test_generator_perform__yearly_reset(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Quote,
            data={
                'format': '{year}-{counter}',
                'reset': 'yearly',
            },
        )

        generator = number_generators.RegularNumberGenerator(item)

        with patch('creme.billing.number_generators.datetime') as mock_datetime1:
            # Mock only datetime.date.today()
            mock_datetime1.date.today.return_value = date(year=2023, month=3, day=25)

            number1 = generator.perform()

        self.assertEqual('2023-1', number1)

        # Still the same year => increment ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime2:
            mock_datetime2.date.today.return_value = date(year=2023, month=11, day=12)

            number2 = generator.perform()

        self.assertEqual('2023-2', number2)

        # Year changes => reset ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime3:
            mock_datetime3.date.today.return_value = date(year=2024, month=2, day=5)

            number3 = generator.perform()

        self.assertEqual('2024-1', number3)

    def test_generator_perform__monthly_reset(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Quote,
            data={
                'format': '{year}-{month}-{counter}',
                'reset': 'monthly',
            },
        )

        generator = number_generators.RegularNumberGenerator(item)

        with patch('creme.billing.number_generators.datetime') as mock_datetime1:
            mock_datetime1.date.today.return_value = date(year=2023, month=3, day=25)

            number1 = generator.perform()

        self.assertEqual('2023-03-1', number1)

        # Still the same month => increment ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime2:
            mock_datetime2.date.today.return_value = date(year=2023, month=3, day=27)

            number2 = generator.perform()

        self.assertEqual('2023-03-2', number2)

        # Month changes => reset ---
        with patch('creme.billing.number_generators.datetime') as mock_datetime3:
            mock_datetime3.date.today.return_value = date(year=2023, month=4, day=5)

            number3 = generator.perform()
            number4 = generator.perform()

        self.assertEqual('2023-04-1', number3)
        self.assertEqual('2023-04-2', number4)

        # Beware: year changes & not month...
        with patch('creme.billing.number_generators.datetime') as mock_datetime3:
            mock_datetime3.date.today.return_value = date(year=2024, month=4, day=5)

            number5 = generator.perform()
        self.assertEqual('2024-04-1', number5)

    def test_generator_perform__format_error(self):
        orga = Organisation.objects.create(
            user=self.get_root_user(), name='Acme', code='ACM',
        )

        item = NumberGeneratorItem.objects.create(
            numbered_type=Quote, organisation=orga,
            data={'format': 'QUO-{invalid}'},
        )

        generator = number_generators.RegularNumberGenerator(item=item)
        with self.assertRaises(ConflictError):
            generator.perform()

    def test_config_brick(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Acme')
        NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{counter:04}', 'reset': 'never'},
        )

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('billing',))
        )
        brick_node = self.get_brick_node(
            tree=self.get_html_tree(response.content),
            brick=NumberGeneratorItemsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Organisation configured for number generation',
            plural_title='{count} Organisations configured for number generation',
        )
        self.assertInstanceLink(brick_node, entity=orga)
        # TODO: complete

    def test_config_edition(self):
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

    def test_config_edition__perm(self):
        self.login_as_standard(allowed_apps=['billing'])  # admin_4_apps=['billing']
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        item = NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{counter:04}', 'reset': 'never'},
        )

        self.assertGET403(reverse('billing__edit_number_generator', args=(item.id,)))

    def test_config_edition__errors(self):
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

    def test_generation__invoice__managed_emitter(self):
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

    def test_generation__invoice__issuing_date(self):
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

    def test_generation__invoice__emitter_not_managed(self):
        "Emitter Organisation is not managed."
        user = self.login_as_root_and_get()

        issuing_date = date(year=2024, month=10, day=21)
        invoice, source, __target = self.create_invoice_n_orgas(
            user=user, name='Invoice001', issuing_date=issuing_date,
        )
        self.assertFalse(invoice.number)
        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=source))

        self.assertPOST404(self._build_number_generation_url(invoice), follow=True)

    def test_generation__quote(self):
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
        self.assertEqual('QU-0001', number)

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

    def test_generation__salesorder(self):
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

    def test_generation__creditnote(self):
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

    def test_generation__bad_type(self):
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        response = self.client.post(self._build_number_generation_url(orga), follow=True)
        self.assertContains(
            response,
            'The entity must be a billing entity',
            status_code=409,
            html=True,
        )

    def test_generation__not_registered_type(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        tpl = TemplateBase.objects.create(
            user=user, name='Acme',
            ct=Invoice, status_uuid=InvoiceStatus.objects.first().uuid,
            source=source, target=target,
        )
        self.assertPOST404(self._build_number_generation_url(tpl))

    def test_descriptions(self):
        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')

        format_str1 = 'INV-{counter:04}'
        self.assertListEqual(
            [
                _('Edition is allowed'),
                _('Pattern: «{}»').format(format_str1),
                _('Current counter: {}').format(1),
                _('Counter reset: {}').format(pgettext('billing-reset', 'Never')),
            ],
            NumberGeneratorItem(
                organisation=orga, numbered_type=Invoice,
                is_edition_allowed=True,
                data={'format': format_str1, 'reset': 'never', 'counter': 1},
            ).description,
        )

        format_str2 = 'QUO-{year}-{counter}'
        self.assertListEqual(
            [
                _('Edition is forbidden'),
                _('Pattern: «{}»').format(format_str2),
                _('Current counter: {}').format(12),
                _('Counter reset: {}').format(_('Yearly')),
            ],
            NumberGeneratorItem(
                organisation=orga, numbered_type=Quote,
                is_edition_allowed=False,
                data={'format': format_str2, 'reset': 'yearly', 'counter': 12},
            ).description,
        )

        format_str3 = 'SO-{year}-{month-}{counter}'
        self.assertListEqual(
            [
                _('Edition is forbidden'),
                _('Pattern: «{}»').format(format_str3),
                _('Current counter: {}').format(1),
                _('Counter reset: {}').format(_('Monthly')),
            ],
            NumberGeneratorItem(
                organisation=orga, numbered_type=SalesOrder,
                is_edition_allowed=False,
                data={'format': format_str3, 'reset': 'monthly'},
            ).description,
        )

        self.assertListEqual(
            ['??'],
            NumberGeneratorItem(organisation=orga, numbered_type=TemplateBase).description,
        )

    def test_invoice_creation__emitter_not_managed__number_not_filled(self):
        user = self.login_as_root_and_get()

        response = self.assertGET200(reverse('billing__create_invoice'))

        with self.assertNoException():
            number_f = response.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        # ---
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice 001')[0]
        self.assertEqual('', invoice.number)

    def test_invoice_creation__emitter_not_managed__number_filled(self):
        user = self.login_as_root_and_get()

        number = 'INV0001'
        invoice = self.create_invoice_n_orgas(user=user, name='Inv#1', number=number)[0]
        self.assertEqual(number, invoice.number)

    def test_invoice_creation__managed_emitter__edition_is_allowed(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        number = 'INV0001'
        invoice = self.create_invoice(
            user=user, name='Invoice001', source=source, target=target,
            number=number,
        )
        self.assertEqual(number, invoice.number)

    def test_invoice_creation__managed_emitter__edition_is_forbidden(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Invoice),
        )
        self.assertTrue(item.is_edition_allowed)

        item.is_edition_allowed = False
        item.save()

        # Error ---
        name = 'Invoice001'
        currency = Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_invoice'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'status': InvoiceStatus.objects.first().id,

                'currency': currency.id,
                'discount': '0',

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

                'number': 'IN010',  # <====
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='number',
            errors=_('The number is set as not editable by the configuration.'),
        )

        # OK ---
        invoice = self.create_invoice(
            user=user, name=name, source=source, target=target, currency=currency,
        )
        self.assertEqual('', invoice.number)

    def test_quote_creation__managed_emitter__edition_is_allowed(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        number = 'QU#0001'
        invoice = self.create_quote(
            user=user, name='Quote001', source=source, target=target,
            number=number,
        )
        self.assertEqual(number, invoice.number)

    def test_quote_creation__managed_emitter__edition_is_forbidden(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        self.assertTrue(item.is_edition_allowed)

        item.data['format'] = 'QUO-{counter:04}'
        item.is_edition_allowed = False
        item.save()

        # Error ---
        name = 'Quote001'
        currency = Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_quote'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'status': QuoteStatus.objects.first().id,

                'currency': currency.id,
                'discount': '0',

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

                'number': 'Q010',  # <====
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='number',
            errors=_('The number is set as not editable by the configuration.'),
        )

        # OK ---
        quote = self.create_quote(
            user=user, name=name, source=source, target=target, currency=currency,
        )
        self.assertEqual('QUO-0001', quote.number)

    def test_invoice_edition(self):
        user = self.login_as_root_and_get()

        number = 'INV001'
        emitter, receiver = self.create_orgas(user=user)
        invoice = self.create_invoice(
            user=user, name='Invoice 001', number=number,
            source=emitter, target=receiver,
        )

        NumberGeneratorItem.objects.create(
            organisation=emitter,
            numbered_type=Invoice,
            is_edition_allowed=False,  # <==
            # data=...
        )

        url = invoice.get_edit_absolute_url()
        self.assertGET200(url)

        # POST (no change) ---
        data = {
            'user': user.pk,
            'name': invoice.name,
            'status': invoice.status_id,
            'currency': invoice.currency_id,
            'discount': '0',

            'number': invoice.number,

            # 'issuing_date':    self.formfield_value_date(2024,  9,  7),
            # 'expiration_date': self.formfield_value_date(2025, 11, 14),

            self.SOURCE_KEY: emitter.id,
            self.TARGET_KEY: self.formfield_value_generic_entity(receiver),
        }
        self.assertNoFormError(self.client.post(url, follow=True, data=data))
        self.assertEqual(number, self.refresh(invoice).number)

        # POST (change) ---
        response3 = self.assertPOST200(url, follow=True, data={**data, 'number': 'INV002'})
        self.assertFormError(
            self.get_form_or_fail(response3),
            field='number',
            errors=_('The number is set as not editable by the configuration.'),
        )

    def test_inner_edition__allowed__emitter_is_managed(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        self.assertTrue(item.is_edition_allowed)

        quote = self.create_quote(user=user, name='Order001', source=source, target=target)
        self.assertStartsWith(quote.number, _('QUO'))

        field_name = 'number'
        uri = self.build_inneredit_uri(quote, field_name)
        response1 = self.assertGET200(uri)
        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            number_f = response1.context['form'].fields[form_field_name]

        self.assertIsInstance(number_f, CharField)
        self.assertEqual(quote.number, number_f.initial)

        # POST ---
        number = 'Q1256'
        self.assertNoFormError(self.client.post(uri, data={form_field_name: number}))
        self.assertEqual(number, self.refresh(quote).number)

    def test_inner_edition__allowed__emitter_is_not_managed(self):
        user = self.login_as_root_and_get()

        quote, source, __target = self.create_quote_n_orgas(user=user, name='Order001')
        self.assertFalse(quote.number)
        self.assertFalse(NumberGeneratorItem.objects.filter(
            organisation=source, numbered_type=quote.entity_type,
        ))

        field_name = 'number'
        uri = self.build_inneredit_uri(quote, field_name)
        response1 = self.assertGET200(uri)
        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            number_f = response1.context['form'].fields[form_field_name]

        self.assertIsInstance(number_f, CharField)

        # POST ---
        number = 'QU125'
        self.assertNoFormError(self.client.post(uri, data={form_field_name: number}))
        self.assertEqual(number, self.refresh(quote).number)

    def test_inner_edition__forbidden(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        NumberGeneratorItem.objects.filter(
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        ).update(is_edition_allowed=False)

        quote = self.create_quote(user=user, name='Order001', source=source, target=target)
        old_number = quote.number
        self.assertStartsWith(old_number, _('QUO'))

        field_name = 'number'
        uri = self.build_inneredit_uri(quote, field_name)

        self.assertContains(
            self.client.get(uri),
            _('The number is set as not editable by the configuration.'),
            html=True,
        )

        # POST ---
        form_field_name = f'override-{field_name}'
        response2 = self.assertPOST200(uri, data={form_field_name: 'Q1256'})
        self.assertFormError(
            self.get_form_or_fail(response2),
            field=form_field_name,
            errors=_('The number is set as not editable by the configuration.'),
        )
        self.assertEqual(old_number, self.refresh(quote).number)

    def _merge_organisations(self, orga1, orga2, swapped=False):
        self.assertNoFormError(self.client.post(
            self.build_merge_url(orga1, orga2),
            follow=True,
            data={
                'user_1':      orga1.user_id,
                'user_2':      orga2.user_id,
                'user_merged': orga1.user_id,

                'name_1':      orga1.name,
                'name_2':      orga2.name,
                'name_merged': orga1.name,
            },
        ))
        if swapped:
            self.assertStillExists(orga2)
            self.assertDoesNotExist(orga1)
        else:
            self.assertStillExists(orga1)
            self.assertDoesNotExist(orga2)

    def test_merge_organisations__first_is_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = create_orga(name='Nerv')

        generators1 = NumberGeneratorItem.objects.filter(organisation=orga1)
        self.assertEqual(4, len(generators1))
        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga2))

        self._merge_organisations(orga1, orga2)

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga2))
        self.maxDiff = None
        self.assertCountEqual(
            generators1, NumberGeneratorItem.objects.filter(organisation=orga1),
        )

    def test_merge_organisations__second_is_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV')
        orga2 = self._set_managed(create_orga(name='Nerv'))

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga1))
        generators2 = NumberGeneratorItem.objects.filter(organisation=orga2)
        self.assertEqual(4, len(generators2))

        self._merge_organisations(orga1, orga2, swapped=True)

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga1))
        self.maxDiff = None
        self.assertCountEqual(
            generators2, NumberGeneratorItem.objects.filter(organisation=orga2),
        )

    def test_merge_organisations__2_managed(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = self._set_managed(create_orga(name='NERV'))
        orga2 = self._set_managed(create_orga(name='Nerv'))

        generators1 = NumberGeneratorItem.objects.filter(organisation=orga1)
        self.assertEqual(4, len(generators1))

        generators2 = NumberGeneratorItem.objects.filter(organisation=orga2)
        self.assertEqual(4, len(generators2))

        self._merge_organisations(orga1, orga2)

        self.assertFalse(NumberGeneratorItem.objects.filter(organisation=orga2))
        self.maxDiff = None
        self.assertCountEqual(
            generators1, NumberGeneratorItem.objects.filter(organisation=orga1),
        )

    def test_action_invoice(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user)
        self._set_managed(source)

        invoice = self.create_invoice(
            user=user, name='Invoice 0001', source=source, target=target,
        )

        action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, GenerateInvoiceNumberAction)
        )
        self.assertEqual('billing-invoice_number', action.id)
        self.assertEqual('billing-number', action.type)
        self.assertEqual(
            reverse('billing__generate_number', args=(invoice.id,)),
            action.url,
        )
        self.assertTrue(action.is_enabled)
        self.assertTrue(action.is_visible)
        self.assertEqual('', action.help_text)
        self.assertDictEqual(
            {
                'data': {},
                'options': {
                    'confirm': _('Do you really want to generate a number?'),
                },
            },
            action.action_data,
        )

    def test_action_invoice__no_config(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice #1')[0]

        action = GenerateInvoiceNumberAction(user=user, instance=invoice)
        self.assertFalse(action.is_enabled)
        self.assertTrue(action.is_visible)
        self.assertEqual(
            _('This entity cannot generate a number (see configuration of the app Billing)'),
            action.help_text,
        )

    def test_action_invoice__number_already_fill(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user)
        self._set_managed(source)

        invoice = self.create_invoice(
            user=user, name='Invoice 0001', source=source, target=target,
            number='J03',
        )

        action = GenerateInvoiceNumberAction(user=user, instance=invoice)
        self.assertFalse(action.is_enabled)
        self.assertTrue(action.is_visible)
        self.assertEqual(_('This entity has already a number'), action.help_text)

    def test_action_quote(self):
        user = self.login_as_root_and_get()
        cnote = self.create_credit_note_n_orgas(user=user, name='Quotee 0001')[0]

        action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=cnote)
            if isinstance(action, GenerateCreditNoteNumberAction)
        )
        self.assertEqual('billing-creditnote_number', action.id)
        self.assertEqual('billing-number', action.type)
        self.assertEqual(
            reverse('billing__generate_number', args=(cnote.id,)),
            action.url,
        )
