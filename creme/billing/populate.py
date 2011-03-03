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

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.utils import create_or_update as create
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD
from creme_core.models import RelationType, SearchConfigItem, ButtonMenuItem
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Organisation, Contact

from billing.models import *
from billing.constants import *
from billing.buttons import generate_invoice_number_button


class Populator(BasePopulator):
    dependencies = ['creme.creme_core', 'creme.persons']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_BILL_ISSUED,   _(u"issued by")),   #[Invoice, Quote, SalesOrder]
                            (REL_OBJ_BILL_ISSUED,   _(u"has issued"),   [Organisation]))
        RelationType.create((REL_SUB_BILL_RECEIVED, _(u"received by")), #[Invoice, Quote, SalesOrder]
                            (REL_OBJ_BILL_RECEIVED, _(u"has received"), [Organisation, Contact]))


        #NB: pk=1 --> default status (used when a quote is converted in invoice for example)
        create(QuoteStatus, 1, name=_(u"Pending")) #default status
        create(QuoteStatus, 2, name=_(u"Accepted"))
        create(QuoteStatus, 3, name=_(u"Rejected"))
        create(QuoteStatus, 4, name=_(u"Created"))

        create(PaymentTerms, 1, name=_(u"30 days")) #default status
        create(PaymentTerms, 2, name=_(u"Cash"))
        create(PaymentTerms, 3, name=_(u"45 days"))
        create(PaymentTerms, 4, name=_(u"60 days"))
        create(PaymentTerms, 5, name=_(u"30 days, end month the 10"))

        create(SalesOrderStatus, 1, name=_(u"Issued"),   is_custom=False) #default status
        create(SalesOrderStatus, 2, name=_(u"Accepted"), is_custom=True)
        create(SalesOrderStatus, 3, name=_(u"Rejected"), is_custom=True)
        create(SalesOrderStatus, 4, name=_(u"Created"),  is_custom=True)

        create(InvoiceStatus, 1, name=_(u"Draft"),               is_custom=False) #default status
        create(InvoiceStatus, 2, name=_(u"To be sent"),          is_custom=False)
        create(InvoiceStatus, 3, name=_(u"Sent"),                is_custom=True)
        create(InvoiceStatus, 4, name=_(u"Resulted"),            is_custom=True)
        create(InvoiceStatus, 5, name=_(u"Partly resulted"),     is_custom=True)
        create(InvoiceStatus, 6, name=_(u"Collection"),          is_custom=True)
        create(InvoiceStatus, 7, name=_(u"Resulted collection"), is_custom=True)
        create(InvoiceStatus, 8, name=_(u"Canceled"),            is_custom=True)

        create(CreditNoteStatus, 1, name=_(u"Draft"),  is_custom=False)
        create(CreditNoteStatus, 2, name=_(u"Issued"), is_custom=True)

        create(ButtonMenuItem, 'billing-generate_invoice_number', content_type=ContentType.objects.get_for_model(Invoice), button_id=generate_invoice_number_button.id_, order=0)

        def create_hf(hf_pk, hfi_pref, name, model):
            hf = HeaderFilter.create(pk=hf_pk, name=name, model=model)
            create(HeaderFilterItem, hfi_pref + 'name',    order=1, name='name',            title=_(u'Name'),            type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="name__icontains")
            create(HeaderFilterItem, hfi_pref + 'number',  order=2, name='number',          title=_(u'Number'),          type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="number__icontains")
            create(HeaderFilterItem, hfi_pref + 'issdate', order=3, name='issuing_date',    title=_(u"Issuing date"),    type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="issuing_date__range")
            create(HeaderFilterItem, hfi_pref + 'expdate', order=4, name='expiration_date', title=_(u"Expiration date"), type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="expiration_date__range")
            create(HeaderFilterItem, hfi_pref + 'status',  order=5, name='status__name',    title=_(u'Status - Name'),   type=HFI_FIELD, header_filter=hf, has_a_filter=True, editable=True, sortable=True, filter_string="status__name__icontains")

        create_hf('billing-hf_invoice',    'billing-hfi_invoice_',    _(u'Invoice view'),     Invoice)
        create_hf('billing-hf_quote',      'billing-hfi_quote_',      _(u'Quote view'),       Quote)
        create_hf('billing-hf_salesorder', 'billing-hfi_salesorder_', _(u'Sales order view'), SalesOrder)
        create_hf('billing-hf_creditnote', 'billing-hfi_creditnote_', _(u'Credit note view'), CreditNote)

        for model in (Invoice, CreditNote, Quote, SalesOrder):
            SearchConfigItem.create(model, ['name', 'number', 'status__name'])
