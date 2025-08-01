from decimal import Decimal

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import Vat
from creme.persons.tests.base import skipIfCustomOrganisation

from .base import (
    ProductLine,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
)


class VatTestCase(_BillingTestCase):
    def _build_edition_url(self, vat):
        return reverse(
            'creme_config__edit_instance', args=('creme_core', 'vat_value', vat.id),
        )

    def test_config_edition__not_used(self):
        self.login_as_root()

        old_value = Decimal('5.00')
        self.assertFalse(Vat.objects.filter(value=old_value))

        vat = Vat.objects.create(value=old_value)

        url = self._build_edition_url(vat)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/edit-popup.html')
        self.assertEqual(
            _('Edit «{object}»').format(object=vat),
            response.context.get('title'),
        )

        # ----
        new_value = Decimal('5.75')
        self.assertFalse(Vat.objects.filter(value=new_value))

        self.assertNoFormError(self.client.post(
            url, data={'value': new_value},
        ))
        self.assertEqual(new_value, self.refresh(vat).value)

    @skipIfCustomOrganisation
    @skipIfCustomProductLine
    @skipIfCustomInvoice
    def test_config_edition__used(self):
        user = self.login_as_root_and_get()

        value = Decimal('5.00')
        self.assertFalse(Vat.objects.filter(value=value))

        vat = Vat.objects.create(value=value)

        invoice = self.create_invoice_n_orgas(user=user, name='Inv-001', vat=vat.id)[0]
        ProductLine.objects.create(
            user=user, related_document=invoice, vat_value=vat,
            on_the_fly_item='toy',
        )
        self.assertGET409(self._build_edition_url(vat))
