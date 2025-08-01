from django.utils.translation import gettext as _

from creme.creme_core.models import Currency
from creme.creme_core.tests.base import CremeTestCase


class CurrencyTestCase(CremeTestCase):
    def test_create(self):
        cur1 = Currency.objects.order_by('id').first()
        self.assertIsInstance(cur1, Currency)
        self.assertEqual(_('Euro'), cur1.name)
        self.assertEqual('€',       cur1.local_symbol)
        self.assertEqual('EUR',     cur1.international_symbol)
        self.assertIs(cur1.is_custom, True)
        self.assertIs(cur1.is_default, True)

        name = 'Flouz'
        local_symbol = 'F'
        international_symbol = 'FLZ'
        create_cur = Currency.objects.create
        cur2 = self.refresh(create_cur(
            name=name,
            local_symbol=local_symbol,
            international_symbol=international_symbol,
        ))
        self.assertEqual(name,                 cur2.name)
        self.assertEqual(local_symbol,         cur2.local_symbol)
        self.assertEqual(international_symbol, cur2.international_symbol)
        self.assertTrue(cur2.is_custom)
        self.assertIs(cur2.is_default, False)

        cur3 = self.refresh(create_cur(
            name='Pez',
            local_symbol='P',
            international_symbol='PZ',
            is_default=True,
        ))
        self.assertTrue(cur3.is_default)
        self.assertFalse(self.refresh(cur2).is_default)
        self.assertFalse(self.refresh(cur1).is_default)  # <==

        self.assertEqual(cur3, Currency.objects.default())

    def test_edit(self):
        cur1 = Currency.objects.order_by('id').first()
        cur2 = Currency.objects.create(
            name='Pez',
            local_symbol='P',
            international_symbol='PZ',
            is_default=True,
        )

        cur2.is_default = False
        cur2.save()

        self.assertFalse(self.refresh(cur1).is_default)
        self.assertTrue(self.refresh(cur2).is_default)

    def test_delete(self):
        cur1 = Currency.objects.order_by('id').first()
        cur2 = Currency.objects.create(
            name='Pez',
            local_symbol='P',
            international_symbol='PZ',
            is_default=True,
        )
        self.assertFalse(self.refresh(cur1).is_default)

        cur2.delete()
        self.assertDoesNotExist(cur2)
        self.assertEqual(1, Currency.objects.filter(is_default=True).count())
