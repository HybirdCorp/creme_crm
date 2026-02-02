from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from creme.billing.models import Line, NumberGeneratorItem, QuoteStatus
from creme.billing.populate import UUID_QUOTE_STATUS_PENDING
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import Vat
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..base import (
    Address,
    ProductLine,
    Quote,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomQuote,
    skipIfCustomServiceLine,
)


class QuoteStatusTestCase(_BillingTestCase):
    def test_create(self):
        statuses = [*QuoteStatus.objects.all()]
        self.assertEqual(4, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertUUIDEqual(UUID_QUOTE_STATUS_PENDING, default_status.uuid)

        # New default status => previous default status is updated
        new_status1 = QuoteStatus.objects.create(name='OK', is_default=True)
        self.assertTrue(self.refresh(new_status1).is_default)
        self.assertEqual(5, QuoteStatus.objects.count())
        self.assertFalse(
            QuoteStatus.objects.exclude(id=new_status1.id).filter(is_default=True)
        )

        # No default status is found => new one is default one
        QuoteStatus.objects.update(is_default=False)
        new_status2 = QuoteStatus.objects.create(name='KO', is_default=False)
        self.assertTrue(self.refresh(new_status2).is_default)

    def test_render(self):
        user = self.get_root_user()
        status = QuoteStatus.objects.create(name='OK', color='00FF00')
        ctxt = {
            'user': user,
            'quote': Quote(user=user, name='OK Quote', status=status),
        }
        template = Template(
            r'{% load creme_core_tags %}'
            r'{% print_field object=quote field="status" tag=tag %}'
        )
        self.assertEqual(
            status.name,
            template.render(Context({**ctxt, 'tag': ViewTag.TEXT_PLAIN})).strip(),
        )
        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            template.render(Context({**ctxt, 'tag': ViewTag.HTML_DETAIL})),
        )


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteTestCase(_BillingTestCase):
    def test_delete(self):
        user = self.login_as_root_and_get()
        quote, source, target = self.create_quote_n_orgas(user=user, name='Nerv')

        kwargs = {
            'user': user, 'related_document': quote,
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

        url = quote.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            quote = self.refresh(quote)

        self.assertIs(quote.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(quote)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)
        self.assertStillExists(source)
        self.assertStillExists(target)

    def test_delete_status(self):
        user = self.login_as_root_and_get()
        new_status = QuoteStatus.objects.first()
        status2del = QuoteStatus.objects.create(name='OK')

        quote = self.create_quote_n_orgas(user=user, name='Nerv', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='quote_status',
            new_status=new_status,
            doc=quote,
        )

    @skipIfCustomAddress
    @skipIfCustomServiceLine
    def test_clone__not_managed_emitter(self):
        "Source Organisation is not managed => no number is set."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        target.billing_address = Address.objects.create(
            name='Billing address 01',
            address='BA1 - Address', city='BA1 - City',
            owner=target,
        )
        target.save()

        # status = QuoteStatus.objects.filter(is_default=False)[0] TODO

        quote = self.create_quote(
            user=user, name='Quote001', source=source, target=target,
            # status=status,
            number='12',
        )
        quote.acceptation_date = date.today()
        quote.save()

        sl = ServiceLine.objects.create(
            related_item=self.create_service(user=user), user=user, related_document=quote,
        )

        address_count = Address.objects.count()

        origin_b_addr = quote.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        cloned = self.clone(quote)
        self.assertIsNone(cloned.acceptation_date)
        # self.assertTrue(cloned.status.is_default) TODO
        self.assertEqual('', cloned.number)

        self.assertNotEqual(quote, cloned)  # Not the same pk
        self.assertEqual(source, cloned.source)
        self.assertEqual(target, cloned.target)

        # Lines are cloned
        cloned_lines = [*cloned.iter_all_lines()]
        self.assertEqual(1, len(cloned_lines))
        self.assertNotEqual([sl], cloned_lines)

        # Addresses are cloned
        self.assertEqual(address_count + 2, Address.objects.count())

        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,                billing_address.owner)
        self.assertEqual(origin_b_addr.name,    billing_address.name)
        self.assertEqual(origin_b_addr.city,    billing_address.city)
        self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)

    def test_clone__managed_emitter(self):
        "Organisation is managed => number is generated (but only once BUGFIX)."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        item.data['format'] = 'QUO-{counter:04}'
        item.save()

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target)
        self.assertEqual('QUO-0001', quote.number)

        cloned = self.clone(quote)
        self.assertEqual('QUO-0002', cloned.number)

    # @skipIfCustomAddress
    # @skipIfCustomServiceLine
    # def test_clone__method01(self):  # DEPRECATED
    #     "Organisation not managed => number is set to '0'."
    #     user = self.login_as_root_and_get()
    #     source, target = self.create_orgas(user=user)
    #
    #     target.billing_address = b_addr = Address.objects.create(
    #         name='Billing address 01',
    #         address='BA1 - Address', city='BA1 - City',
    #         owner=target,
    #     )
    #     target.save()
    #
    #     quote = self.create_quote(
    #         user=user, name='Quote001', source=source, target=target,
    #         # status=status,
    #         number='12',
    #     )
    #     quote.acceptation_date = date.today()
    #     quote.save()
    #
    #     sl = ServiceLine.objects.create(
    #         related_item=self.create_service(user=user), user=user, related_document=quote,
    #     )
    #
    #     cloned = self.refresh(quote.clone())
    #     quote = self.refresh(quote)
    #
    #     self.assertIsNone(cloned.acceptation_date)
    #     self.assertEqual('', cloned.number)
    #
    #     self.assertNotEqual(quote, cloned)  # Not the same pk
    #     self.assertEqual(source, cloned.source)
    #     self.assertEqual(target, cloned.target)
    #
    #     # Lines are cloned
    #     cloned_lines = [*cloned.iter_all_lines()]
    #     self.assertEqual(1, len(cloned_lines))
    #     self.assertNotEqual([sl], cloned_lines)
    #
    #     # Addresses are cloned
    #     billing_address = cloned.billing_address
    #     self.assertIsInstance(billing_address, Address)
    #     self.assertEqual(cloned,      billing_address.owner)
    #     self.assertEqual(b_addr.name, billing_address.name)
    #     self.assertEqual(b_addr.city, billing_address.city)
    #
    # def test_clone__method02(self):  # DEPRECATED
    #     "Organisation is managed => number is generated (but only once BUGFIX)."
    #     user = self.login_as_root_and_get()
    #
    #     source, target = self.create_orgas(user=user)
    #     self._set_managed(source)
    #
    #     item = self.get_object_or_fail(
    #         NumberGeneratorItem,
    #         organisation=source,
    #         numbered_type=ContentType.objects.get_for_model(Quote),
    #     )
    #     item.data['format'] = 'QUO-{counter:04}'
    #     item.save()
    #
    #     quote = self.create_quote(user=user, name='My Quote', source=source, target=target)
    #     self.assertEqual('QUO-0001', quote.number)
    #
    #     cloned = quote.clone()
    #     self.assertEqual('QUO-0002', cloned.number)

    def test_num_queries(self):
        """Avoid the queries about line sa creation
        (because these queries can be really slow with a lot of entities)
        """
        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        user = self.login_as_root_and_get()

        # NB: we do not use assertNumQueries, because external
        #     signal handlers can add their owns queries
        context = CaptureQueriesContext(connections[DEFAULT_DB_ALIAS])

        status = QuoteStatus.objects.all()[0]
        source, target = self.create_orgas(user=user)

        with context:
            quote = Quote.objects.create(
                user=user, name='My Quote', status=status,
                source=source, target=target,
            )

        self.assertTrue(quote.pk)
        self.assertEqual(0, quote.total_no_vat)
        self.assertEqual(0, quote.total_vat)

        for query_info in context.captured_queries:
            query = query_info['sql']
            self.assertNotIn('billing_productline', query)
            self.assertNotIn('billing_serviceline', query)
