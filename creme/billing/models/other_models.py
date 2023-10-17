################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from __future__ import annotations

import logging
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.transaction import atomic
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.global_info import get_per_request_cache
from creme.creme_core.models import base
from creme.creme_core.models import fields as core_fields

logger = logging.getLogger(__name__)


class SettlementTerms(base.MinionModel):
    name = models.CharField(_('Settlement terms'), max_length=100)

    creation_label = _('Create settlement terms')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', 'Settlement terms')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Settlement terms')
        ordering = ('name',)


class StatusManager(base.MinionManager):
    def __init__(self):
        super().__init__()
        self._cache_key = None

    def default(self):
        # NB: contribute_to_class() is called with <AbstractStatus>,
        #     not InvoiceStatus/QuoteStatus/...
        cache_key = self._cache_key
        if cache_key is None:
            self._cache_key = cache_key = f'billing-default_{self.model.__name__.lower()}'

        cache = get_per_request_cache()

        try:
            status = cache[cache_key]
        except KeyError:
            cache[cache_key] = status = self.filter(is_default=True).first()

        return status


class AbstractStatus(base.MinionModel):
    name = models.CharField(_('Name'), max_length=100)
    order = core_fields.BasicAutoField()
    color = core_fields.ColorField(default=core_fields.ColorField.random)
    is_default = models.BooleanField(_('Is default?'), default=False)

    creation_label = pgettext_lazy('billing-status', 'Create a status')

    objects = StatusManager()

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        app_label = 'billing'
        ordering = ('order',)

    # TODO: create a function/ an abstract model for saving model with
    #       is_default attribute (and use it for Vat too) ??
    @atomic
    def save(self, *args, **kwargs):
        model = type(self)
        if self.is_default:
            model.objects.filter(is_default=True).update(is_default=False)
        elif not model.objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super().save(*args, **kwargs)


class InvoiceStatus(AbstractStatus):
    pending_payment = models.BooleanField(_('Pending payment'), default=False)
    is_validated = models.BooleanField(
        _('Is validated?'), default=False,
        help_text=_('If true, the status is used when an Invoice number is generated.'),
    )

    # TODO: factorise too
    @atomic
    def save(self, *args, **kwargs):
        model = type(self)
        if self.is_validated:
            model.objects.filter(is_validated=True).update(is_validated=False)
        elif not model.objects.filter(is_validated=True).exclude(pk=self.id).exists():
            self.is_validated = True

        super().save(*args, **kwargs)

    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _('Invoice status')
        verbose_name_plural = _('Invoice statuses')


class QuoteStatus(AbstractStatus):
    won = models.BooleanField(pgettext_lazy('billing-quote_status', 'Won'), default=False)

    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _('Quote status')
        verbose_name_plural = _('Quote statuses')


class SalesOrderStatus(AbstractStatus):
    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _('Sales order status')
        verbose_name_plural = _('Sales order statuses')


class CreditNoteStatus(AbstractStatus):
    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _('Credit note status')
        verbose_name_plural = _('Credit note statuses')


class AdditionalInformation(base.MinionModel):
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(verbose_name=_('Description'), blank=True)

    creation_label = pgettext_lazy('billing-additional_info', 'Create information')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = pgettext_lazy('billing-singular', 'Additional information')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Additional information')
        ordering = ('name',)


class PaymentTerms(base.MinionModel):
    name = models.CharField(pgettext_lazy('billing-singular', 'Payment terms'), max_length=100)
    description = models.TextField(verbose_name=_('Description'), blank=True)

    creation_label = _('Create payment terms')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', 'Payment terms')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Payment terms')
        ordering = ('name',)


class PaymentInformationManager(models.Manager):
    def get_by_portable_key(self, key) -> PaymentInformation:
        return self.get(uuid=key)


class PaymentInformation(base.CremeModel):
    uuid = models.UUIDField(
        unique=True, editable=False, default=uuid4,
    ).set_tags(viewable=False)
    name = models.CharField(_('Name'), max_length=200)

    bank_code = models.CharField(_('Bank code'), max_length=12, blank=True)
    counter_code = models.CharField(_('Counter code'), max_length=12, blank=True)
    account_number = models.CharField(_('Account number'), max_length=12, blank=True)
    rib_key = models.CharField(_('RIB key'), max_length=12, blank=True)
    banking_domiciliation = models.CharField(
        _('Banking domiciliation'), max_length=200, blank=True,
    )

    iban = models.CharField(_('IBAN'), max_length=100, blank=True)
    bic = models.CharField(_('BIC'), max_length=100, blank=True)

    is_default = models.BooleanField(_('Is default?'), default=False)
    organisation = models.ForeignKey(
        settings.PERSONS_ORGANISATION_MODEL,
        verbose_name=pgettext_lazy('billing', 'Target organisation'),
        related_name='PaymentInformationOrganisation_set',
        on_delete=models.CASCADE,
    )

    # Can be used by third party code to store the data they want,
    # without having to modify the code.
    extra_data = models.JSONField(editable=False, default=dict).set_tags(viewable=False)

    objects = PaymentInformationManager()

    creation_label = _('Create a payment information')
    save_label     = _('Save the payment information')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', 'Payment information')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Payment information')
        ordering = ('name',)

    # TODO: create a function/ an abstract model for saving model with
    #       is_default attribute (and use it for Vat too) ??
    @atomic
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentInformation.objects.filter(
                organisation=self.organisation, is_default=True,
            ).update(is_default=False)
        elif not PaymentInformation.objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super().save(*args, **kwargs)

    @atomic
    def delete(self, *args, **kwargs):
        if self.is_default:
            first_pi = PaymentInformation.objects.filter(
                organisation=self.organisation,
            ).exclude(id=self.id).first()

            if first_pi:
                first_pi.is_default = True
                first_pi.save()

        super().delete(*args, **kwargs)

    def get_edit_absolute_url(self):
        return reverse('billing__edit_payment_info', args=(self.id,))

    def get_related_entity(self):
        return self.organisation

    def portable_key(self) -> str:
        return str(self.uuid)


# Function used for default field values ---------------------------------------
def _get_default_status_pk(status_model):
    status = status_model.objects.default()
    if status is None:
        logger.warning('No default instance found for %s.', status_model)
        return None

    return status.pk


def get_default_credit_note_status_pk():
    return _get_default_status_pk(CreditNoteStatus)


def get_default_invoice_status_pk():
    return _get_default_status_pk(InvoiceStatus)


def get_default_quote_status_pk():
    return _get_default_status_pk(QuoteStatus)


def get_default_sales_order_status_pk():
    return _get_default_status_pk(SalesOrderStatus)
