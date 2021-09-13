# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial

from creme.creme_core.models import Vat
from creme.creme_core.tests.base import CremeTestCase


class VatTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._vat_backup = [*Vat.objects.all()]
        Vat.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        Vat.objects.all().delete()
        Vat.objects.bulk_create(cls._vat_backup)

    def test_create01(self):
        create_vat = Vat.objects.create
        vat01 = create_vat(value=Decimal('5.0'), is_default=True, is_custom=False)

        vat01 = self.refresh(vat01)
        self.assertEqual(Decimal('5.0'), vat01.value)
        self.assertTrue(vat01.is_default)
        self.assertFalse(vat01.is_custom)

        vat02 = create_vat(value=Decimal('6.0'), is_default=False, is_custom=True)
        vat02 = self.refresh(vat02)
        self.assertEqual(Decimal('6.0'), vat02.value)
        self.assertFalse(vat02.is_default)
        self.assertTrue(vat02.is_custom)

        self.assertEqual(vat01, Vat.get_default_vat())
        self.assertEqual(vat01, Vat.objects.default())

    def test_create02(self):
        vat = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        self.assertTrue(self.refresh(vat).is_default)

    def test_create03(self):
        create_vat = partial(Vat.objects.create, is_default=True, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'))
        vat02 = create_vat(value=Decimal('7.0'))
        self.assertFalse(self.refresh(vat01).is_default)
        self.assertTrue(self.refresh(vat02).is_default)
        self.assertEqual(vat02, Vat.get_default_vat())
        self.assertEqual(vat02, Vat.objects.default())

    def test_edit01(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'), is_default=False)
        vat02 = create_vat(value=Decimal('7.0'), is_default=True)

        vat01.is_default = True
        vat01.save()

        self.assertTrue(self.refresh(vat01).is_default)
        self.assertFalse(self.refresh(vat02).is_default)

    def test_edit02(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'), is_default=False)
        vat02 = create_vat(value=Decimal('7.0'), is_default=True)

        vat02.is_default = False
        vat02.save()

        self.assertFalse(self.refresh(vat01).is_default)
        self.assertTrue(self.refresh(vat02).is_default)

    def test_delete(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat01 = create_vat(value=Decimal('5.0'), is_default=False)
        vat02 = create_vat(value=Decimal('7.0'), is_default=True)

        vat02.delete()

        self.assertTrue(self.refresh(vat01).is_default)
