# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

#import logging
from decimal import Decimal

from django.db.models import ForeignKey, CharField, IntegerField, DecimalField, BooleanField, TextField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, CremeModel

from billing.constants import DEFAULT_VAT
from billing.utils import round_to_2


default_decimal = Decimal()

class Line(CremeModel):
    on_the_fly_item = CharField(_(u'Ligne à la volée'), max_length=100, blank=False, null=True)

    document        = ForeignKey(CremeEntity, verbose_name=_(u'Relatif à'), blank=False, null=False, related_name='billing_lines_set')

    comment         = TextField(_('Remarques'), blank=True, null=True)
    quantity        = IntegerField(_(u'Quantité'), blank=False, null=False, default=0)
    unit_price      = DecimalField(_(u'Prix Unitaire'), max_digits=10, decimal_places=2, blank=True, default=default_decimal)
    discount        = DecimalField(_(u'Remise'), max_digits=10, decimal_places=2, blank=True, default=default_decimal)
    credit          = DecimalField(_(u'Avoir'), max_digits=10, decimal_places=2, blank=True, default=default_decimal)
    total_discount  = BooleanField(_('Remise globale ?'))
    vat             = DecimalField(_(u'TVA'), max_digits=4, decimal_places=2, blank=True, default=DEFAULT_VAT)
    is_paid         = BooleanField(_(u'Réglé ?'))

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Ligne')
        verbose_name_plural = _(u'Lignes')

    def get_price_inclusive_of_tax(self):
        if self.total_discount:
            total =  self.quantity * self.unit_price - self.discount
        else:
            total = self.quantity * (self.unit_price - self.discount)

        vat = total * self.vat / 100
        return round_to_2(total + vat)

    def get_price_exclusive_of_tax(self):
        if self.total_discount:
            return round_to_2(self.quantity * self.unit_price - self.discount)
        else:
            return round_to_2(self.quantity * (self.unit_price - self.discount))

    def clone(self):
        clone = self.__class__()
        clone.on_the_fly_item   = self.on_the_fly_item
        clone.document          = self.document
        clone.comment           = self.comment
        clone.quantity          = self.quantity
        clone.unit_price        = self.unit_price
        clone.discount          = self.discount
        clone.credit            = self.credit
        clone.total_discount    = self.total_discount
        clone.vat               = self.vat
        clone.is_paid           = self.is_paid
        return clone
