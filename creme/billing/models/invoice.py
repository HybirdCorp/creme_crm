# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.db.models import ForeignKey
from django.utils.translation import ugettext_lazy as _

from base import Base
from other_models import InvoiceStatus, SettlementTerms
from product_line import ProductLine
from service_line import ServiceLine


class Invoice(Base):
    status       = ForeignKey(InvoiceStatus, verbose_name=_(u'Status of invoice'), blank=False, null=False)
    payment_type = ForeignKey(SettlementTerms, verbose_name=_(u'Settlement terms'), blank=True, null=True)

    research_fields = Base.research_fields + ['status__name']
    excluded_fields_in_html_output = Base.excluded_fields_in_html_output + ['base_ptr']
    header_filter_exclude_fields = Base.header_filter_exclude_fields + ['base_ptr'] #TODO: use a set() ??

    generate_number_in_create = False

    class Meta:
        app_label = "billing"
        verbose_name = _(u'Invoice')
        verbose_name_plural = _(u'Invoices')

    def get_absolute_url(self):
        return "/billing/invoice/%s" % self.id

    def get_edit_absolute_url(self):
        return "/billing/invoice/edit/%s" % self.id

    @staticmethod
    def get_lv_absolute_url():
        """url for list_view """
        return "/billing/invoices"

    #TODO: use sum()....
    def get_products_price_inclusive_of_tax(self): #TODO: useless ??
        total = 0
        for line in ProductLine.objects.filter(document=self):
            total += line.get_price_inclusive_of_tax()
        return total

    def get_services_price_inclusive_of_tax(self): #TODO: useless ??
        #debug("GET TOTAL SERVICE TTC")
        total = 0
        for line in ServiceLine.objects.filter(document=self):
            total += line.get_price_inclusive_of_tax()
        return total

    def get_products_price_exclusive_of_tax(self): #TODO: useless ??
        total = 0
        for line in ProductLine.objects.filter(document=self):
            total += line.get_price_exclusive_of_tax()
        return total

    def get_services_price_exclusive_of_tax(self): #TODO: useless ??
        #debug("GET TOTAL SERVICE HT")
        total = 0
        for line in ServiceLine.objects.filter(document=self):
            total += line.get_price_exclusive_of_tax()
        return total

    def remaining_payment_for_products(self): #TODO: useless ??
        total = 0
        for line in ProductLine.objects.filter(document=self):
            if not line.is_paid:
                total += line.get_price_inclusive_of_tax()
        return total

    def remaining_payment_for_services(self): #TODO: useless ??
        total = 0
        for line in ServiceLine.objects.filter(document=self):
            if not line.is_paid:
                total += line.get_price_inclusive_of_tax()
        return total

    def build(self, template):
        # Specific recurrent generation rules
        self.status = InvoiceStatus.objects.get(pk=template.status_id) #TODO: "self.status_id = template.status_id" instead ???
        return super(Invoice, self).build(template)

