from datetime import date
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from creme.billing import number_generators
from creme.billing.core.number_generation import (
    NumberGenerator,
    NumberGeneratorRegistry,
)
from creme.billing.models import NumberGeneratorItem
from creme.creme_core.core.exceptions import ConflictError

from ..base import (
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    _BillingTestCase,
)


class NumberGenerationTestCase(_BillingTestCase):
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
