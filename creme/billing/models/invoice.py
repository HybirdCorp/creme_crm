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

from django.db.models import ForeignKey, PROTECT
from django.utils.translation import ugettext_lazy as _

from persons.workflow import transform_target_into_customer

from base import Base
from templatebase import TemplateBase
from other_models import InvoiceStatus, SettlementTerms
from product_line import ProductLine
from service_line import ServiceLine


class Invoice(Base):
    status       = ForeignKey(InvoiceStatus, verbose_name=_(u'Status of invoice'), on_delete=PROTECT)
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

# Commented on 9/1/2012
#    def get_products_price_inclusive_of_tax(self): #todo: use sum()....
#        total = 0
#        for line in ProductLine.objects.filter(document=self):
#            total += line.get_price_inclusive_of_tax()
#        return total
#
#    def get_services_price_inclusive_of_tax(self):
#        #debug("GET TOTAL SERVICE TTC")
#        total = 0
#        for line in ServiceLine.objects.filter(document=self):
#            total += line.get_price_inclusive_of_tax()
#        return total
#
#    def get_products_price_exclusive_of_tax(self):
#        total = 0
#        for line in ProductLine.objects.filter(document=self):
#            total += line.get_price_exclusive_of_tax()
#        return total
#
#    def get_services_price_exclusive_of_tax(self):
#        #debug("GET TOTAL SERVICE HT")
#        total = 0
#        for line in ServiceLine.objects.filter(document=self):
#            total += line.get_price_exclusive_of_tax()
#        return total

    def build(self, template):
        # Specific recurrent generation rules
        status_id = 1 #default status (see populate.py)

        if isinstance(template, TemplateBase):
            tpl_status_id = template.status_id
            if InvoiceStatus.objects.filter(pk=tpl_status_id).exists():
                status_id = tpl_status_id

        self.status_id = status_id
        super(Invoice, self).build(template)
        transform_target_into_customer(self.get_source(), self.get_target(), self.user)

        return self
