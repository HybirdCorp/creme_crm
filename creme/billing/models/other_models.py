# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.conf import settings
from django.db import models
from django.db.transaction import atomic
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.models import CremeModel
from creme.creme_core.models.fields import BasicAutoField


class SettlementTerms(CremeModel):
    name = models.CharField(_('Settlement terms'), max_length=100)

    creation_label = _('Create settlement terms')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', 'Settlement terms')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Settlement terms')
        ordering = ('name',)


class AbstractStatus(CremeModel):
    name = models.CharField(_('Name'), max_length=100)

    # Used by creme_config
    is_custom = models.BooleanField(default=True).set_tags(viewable=False)
    order = BasicAutoField(_('Order'))

    creation_label = pgettext_lazy('billing-status', 'Create a status')

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        app_label = 'billing'
        ordering = ('order',)


class InvoiceStatus(AbstractStatus):
    pending_payment = models.BooleanField(_('Pending payment'), default=False)

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


class AdditionalInformation(CremeModel):
    name = models.CharField(_('Name'), max_length=100)
    description = models.TextField(verbose_name=_('Description'), blank=True)
    is_custom = models.BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config

    creation_label = pgettext_lazy('billing-additional_info', 'Create information')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = pgettext_lazy('billing-singular', 'Additional information')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Additional information')
        ordering = ('name',)


class PaymentTerms(CremeModel):
    name = models.CharField(pgettext_lazy('billing-singular', 'Payment terms'), max_length=100)
    description = models.TextField(verbose_name=_('Description'), blank=True)
    is_custom = models.BooleanField(default=True).set_tags(viewable=False)  # Used by creme_config

    creation_label = _('Create payment terms')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', 'Payment terms')
        verbose_name_plural = pgettext_lazy('billing-plural',   'Payment terms')
        ordering = ('name',)


class PaymentInformation(CremeModel):
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
