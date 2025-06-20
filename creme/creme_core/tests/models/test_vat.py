from decimal import Decimal
from functools import partial

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

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
        vat1 = self.refresh(
            create_vat(value=Decimal('5.0'), is_default=True, is_custom=False)
        )

        self.assertEqual(Decimal('5.0'), vat1.value)
        self.assertTrue(vat1.is_default)
        self.assertFalse(vat1.is_custom)

        with override_language('en'):
            en_str = str(vat1)
        self.assertEqual('5.00 %', en_str)

        with override_language('fr'):
            fr_str = str(vat1)
        self.assertEqual('5,00 %', fr_str)

        # ---
        vat2 = self.refresh(
            create_vat(value=Decimal('6.0'), is_default=False, is_custom=True)
        )
        self.assertEqual(Decimal('6.0'), vat2.value)
        self.assertFalse(vat2.is_default)
        self.assertTrue(vat2.is_custom)

        self.assertEqual(vat1, Vat.objects.default())

    def test_create02(self):
        vat = Vat.objects.create(value=Decimal('5.0'), is_default=False, is_custom=False)
        self.assertTrue(self.refresh(vat).is_default)

    def test_create03(self):
        create_vat = partial(Vat.objects.create, is_default=True, is_custom=False)
        vat1 = create_vat(value=Decimal('5.0'))
        vat2 = create_vat(value=Decimal('7.0'))
        self.assertFalse(self.refresh(vat1).is_default)
        self.assertTrue(self.refresh(vat2).is_default)
        self.assertEqual(vat2, Vat.objects.default())

    def test_edit01(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat1 = create_vat(value=Decimal('5.0'), is_default=False)
        vat2 = create_vat(value=Decimal('7.0'), is_default=True)

        vat1.is_default = True
        vat1.save()

        self.assertTrue(self.refresh(vat1).is_default)
        self.assertFalse(self.refresh(vat2).is_default)

    def test_edit02(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat1 = create_vat(value=Decimal('5.0'), is_default=False)
        vat2 = create_vat(value=Decimal('7.0'), is_default=True)

        vat2.is_default = False
        vat2.save()

        self.assertFalse(self.refresh(vat1).is_default)
        self.assertTrue(self.refresh(vat2).is_default)

    def test_delete(self):
        create_vat = partial(Vat.objects.create, is_custom=False)
        vat1 = create_vat(value=Decimal('5.0'), is_default=False)
        vat2 = create_vat(value=Decimal('7.0'), is_default=True)

        vat2.delete()

        self.assertTrue(self.refresh(vat1).is_default)

    def test_clean(self):
        value = Decimal('5.0')
        vat1 = Vat(value=value)
        with self.assertNoException():
            vat1.clean()
        vat1.save()

        vat2 = Vat(value=value, is_default=True)
        with self.assertRaises(ValidationError) as cm:
            vat2.clean()
        self.assertValidationError(
            cm.exception,
            messages={'value': _('There is already a VAT with this value.')},
            # codes='...',
        )

        vat2.value = Decimal('5.5')
        with self.assertNoException():
            vat2.clean()
        vat2.save()

        vat1.is_default = True  # Edit with the same "value" => no error
        with self.assertNoException():
            vat1.clean()
