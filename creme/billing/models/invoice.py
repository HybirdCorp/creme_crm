# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

from django.core.urlresolvers import reverse
from django.db.models import ForeignKey, PROTECT, SET_NULL
from django.utils.translation import ugettext_lazy as _

from creme.persons.workflow import transform_target_into_customer

from .. import get_template_base_model
from .base import Base
#from .templatebase import TemplateBase
from .other_models import InvoiceStatus, SettlementTerms


#class Invoice(Base):
class AbstractInvoice(Base):
    status       = ForeignKey(InvoiceStatus, verbose_name=_(u'Status of invoice'), on_delete=PROTECT)
    payment_type = ForeignKey(SettlementTerms, verbose_name=_(u'Settlement terms'), blank=True, null=True,
                              on_delete=SET_NULL)

    creation_label = _('Add an invoice')
    generate_number_in_create = False

#    class Meta:
    class Meta(Base.Meta):
        abstract = True
#        app_label = "billing"
        verbose_name = _(u'Invoice')
        verbose_name_plural = _(u'Invoices')

    def get_absolute_url(self):
#        return "/billing/invoice/%s" % self.id
        return reverse('billing__view_invoice', args=(self.id,))

    def get_edit_absolute_url(self):
#        return "/billing/invoice/edit/%s" % self.id
        return reverse('billing__edit_invoice', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
#        return "/billing/invoices"
        return reverse('billing__list_invoices')

    def build(self, template):
        # Specific recurrent generation rules
        status_id = 1 #default status (see populate.py)

#        if isinstance(template, TemplateBase):
        if isinstance(template, get_template_base_model()):
            tpl_status_id = template.status_id
            if InvoiceStatus.objects.filter(pk=tpl_status_id).exists():
                status_id = tpl_status_id

        self.status_id = status_id
#        super(Invoice, self).build(template)
        super(AbstractInvoice, self).build(template)
        transform_target_into_customer(self.get_source(), self.get_target(), self.user)

        return self


class Invoice(AbstractInvoice):
    class Meta(AbstractInvoice.Meta):
        swappable = 'BILLING_INVOICE_MODEL'
