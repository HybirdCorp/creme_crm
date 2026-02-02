from creme.billing import converters
from creme.billing.core.conversion import ConverterRegistry

from ..base import Invoice, Quote, _BillingTestCase


class ConversionTestCase(_BillingTestCase):
    def test_registry(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        registry = ConverterRegistry()
        self.assertIsNone(
            registry.get_converter_class(source_model=Quote, target_model=Invoice),
        )
        self.assertIsNone(
            registry.get_converter(user=user, source=quote, target_model=Invoice),
        )
        self.assertFalse([*registry.models])

        registry.register(
            source_model=Quote,
            target_model=Invoice,
            converter_class=converters.QuoteToInvoiceConverter,
        )
        self.assertIs(
            registry.get_converter_class(source_model=Quote, target_model=Invoice),
            converters.QuoteToInvoiceConverter,
        )
        self.assertIsNone(
            registry.get_converter_class(source_model=Invoice, target_model=Quote),
        )
        self.assertListEqual([(Quote, Invoice)], [*registry.models])

        converter = registry.get_converter(user=user, source=quote, target_model=Invoice)
        self.assertIsInstance(converter, converters.QuoteToInvoiceConverter)
        self.assertEqual(user,    converter.user)
        self.assertEqual(quote,   converter.source)
        self.assertEqual(Invoice, converter.target_model)

        # Duplicate ---
        with self.assertRaises(ConverterRegistry.RegistrationError):
            registry.register(
                source_model=Quote,
                target_model=Invoice,
                converter_class=converters.QuoteToSalesOrderConverter,
            )

        # Unregister ---
        registry.unregister(source_model=Quote, target_model=Invoice)
        self.assertIsNone(
            registry.get_converter_class(source_model=Quote, target_model=Invoice),
        )

        with self.assertRaises(ConverterRegistry.UnRegistrationError):
            registry.unregister(source_model=Quote, target_model=Invoice)

    # TODO: test Converter.check_permissions()
    # TODO: test Converter.perform()
