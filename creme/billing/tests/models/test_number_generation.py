from functools import partial

from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.billing.models import NumberGeneratorItem
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    TemplateBase,
    _BillingTestCase,
)


@skipIfCustomOrganisation
class NumberGenerationTestCase(BrickTestCaseMixin, _BillingTestCase):
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
