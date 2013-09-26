# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.db.models import CharField, BooleanField, TextField, DecimalField, PositiveIntegerField, ForeignKey
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.models import CremeModel

from creme.persons.models import Organisation

from ..constants import DEFAULT_VAT


class SettlementTerms(CremeModel):
    name = CharField(_(u'Settlement terms'), max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Settlement terms')
        verbose_name_plural = _(u'Settlement terms')


class AbstractStatus(CremeModel):
    name      = CharField(_(u'Status'), max_length=100)
    is_custom = BooleanField(default=True).set_tags(viewable=False) #used by creme_config
    order     = PositiveIntegerField(_(u"Order"), default=1, editable=False) #used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True
        app_label = 'billing'
        ordering = ('order',)


class InvoiceStatus(AbstractStatus):
    pending_payment = BooleanField(_(u'Pending payment'), default=False)

    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _(u'Invoice status')
        verbose_name_plural = _(u'Invoice statuses')


class QuoteStatus(AbstractStatus):
    won = BooleanField(_(u'Won'), default=False)

    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _(u'Quote status')
        verbose_name_plural = _(u'Quote statuses')


class SalesOrderStatus(AbstractStatus):
    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _(u'Sales order status')
        verbose_name_plural = _(u'Sales order statuses')


class CreditNoteStatus(AbstractStatus):
    class Meta(AbstractStatus.Meta):
        abstract = False
        verbose_name        = _(u'Credit note status')
        verbose_name_plural = _(u'Credit note statuses')


class AdditionalInformation(CremeModel):
    name        = CharField(_(u'Name'), max_length=100)
    description = TextField(verbose_name=_(u"Description"), blank=True, null=True)
    is_custom   = BooleanField(default=True).set_tags(viewable=False) #used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', u"Additional information")
        verbose_name_plural = pgettext_lazy('billing-plural',   u"Additional information")


class PaymentTerms(CremeModel):
    name        = CharField(_(u'Payment terms'), max_length=100)
    description = TextField(verbose_name=_(u"Description"), blank=True, null=True)
    is_custom   = BooleanField(default=True).set_tags(viewable=False) #used by creme_config

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Payment terms')
        verbose_name_plural = _(u'Payments terms')


class PaymentInformation(CremeModel):
    name                  = CharField(_(u'Name'), max_length=200)

    bank_code             = CharField(_(u'Bank code'), max_length=12, blank=True, null=True)
    counter_code          = CharField(_(u'Counter code'), max_length=12, blank=True, null=True)
    account_number        = CharField(_(u'Account number'), max_length=12, blank=True, null=True)
    rib_key               = CharField(_(u'RIB key'), max_length=12, blank=True, null=True)
    banking_domiciliation = CharField(_(u'Banking domiciliation'), max_length=200, blank=True, null=True)

    iban                  = CharField(_(u'IBAN'), max_length=100, blank=True, null=True)
    bic                   = CharField(_(u'BIC'), max_length=100, blank=True, null=True)

    is_default            = BooleanField(_(u'Is default?'), default=False)
    organisation          = ForeignKey(Organisation, verbose_name=_(u'Target organisation'), related_name='PaymentInformationOrganisation_set')

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name        = pgettext_lazy('billing-singular', u'Payment information')
        verbose_name_plural = pgettext_lazy('billing-plural',   u'Payment information')

    #TODO: create a function/ an abstract model for saving model with is_default attribute (and use it for Vat too) ???
    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentInformation.objects.filter(organisation=self.organisation, is_default=True).update(is_default=False)
        elif not PaymentInformation.objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super(PaymentInformation, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_default:
            existing_pi = PaymentInformation.objects.filter(organisation=self.organisation) \
                                                    .exclude(id=self.id)[:1]

            if existing_pi:
                first_pi = existing_pi[0]
                first_pi.is_default = True
                first_pi.save()

        super(PaymentInformation, self).delete(*args, **kwargs)

    def get_related_entity(self):
        return self.organisation


class Vat(CremeModel):
    value       = DecimalField(_(u'VAT'), max_digits=4, decimal_places=2, default=DEFAULT_VAT)
    is_default  = BooleanField(_(u'Is default?'), default=False)
    is_custom   = BooleanField(default=True).set_tags(viewable=False) #used by creme_config

    def __unicode__(self):
        return unicode(self.value)

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'VAT')
        verbose_name_plural = _(u'VAT')

    def save(self, *args, **kwargs):
        if self.is_default:
            Vat.objects.update(is_default=False)
        elif not Vat.objects.filter(is_default=True).exclude(pk=self.id).exists():
            self.is_default = True

        super(Vat, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_default:
            existing_vat = Vat.objects.exclude(id=self.id)[:1]

            if existing_vat:
                first_vat = existing_vat[0]
                first_vat.is_default = True
                first_vat.save()

        super(Vat, self).delete(*args, **kwargs)

    @staticmethod
    def get_default_vat():
        return Vat.objects.filter(is_default=True)[0]
