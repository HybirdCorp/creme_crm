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
from creme_config.models.setting import SettingKey, SettingKey, SettingValue, SettingValue

from creme_core.utils import create_or_update as create
from creme_core.models.header_filter import HeaderFilterItem, HeaderFilter, HFI_FIELD, HFI_FUNCTION
from creme_core.models import RelationType, SearchConfigItem, ButtonMenuItem
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Organisation, Contact

from billing.models import *
from billing.constants import *
from billing.buttons import generate_invoice_number_button

from products.models import Product, Service


class Populator(BasePopulator):
    dependencies = ['creme.creme_core', 'creme.persons']

    def populate(self, *args, **kwargs):
        billing_entities = [Invoice, Quote, SalesOrder, CreditNote, TemplateBase]
        line_entities = [Line, ProductLine, ServiceLine]
        RelationType.create((REL_SUB_BILL_ISSUED,   _(u"issued by"),    billing_entities),
                            (REL_OBJ_BILL_ISSUED,   _(u"has issued"),   [Organisation])
                           )
        RelationType.create((REL_SUB_BILL_RECEIVED, _(u"received by"),  billing_entities),
                            (REL_OBJ_BILL_RECEIVED, _(u"has received"), [Organisation, Contact])
                           )
        RelationType.create((REL_SUB_HAS_LINE, _(u"had the line"),   billing_entities),
                            (REL_OBJ_HAS_LINE, _(u"is the line of"), line_entities),
                            is_internal=True
                           )
        RelationType.create((REL_SUB_LINE_RELATED_ITEM, _(u"has the related item"),   line_entities),
                            (REL_OBJ_LINE_RELATED_ITEM, _(u"is the related item of"), [Product, Service]),
                            is_internal=True
                           )

        #NB: pk=1 --> default status (used when a quote is converted in invoice for example)
        create(QuoteStatus, 1, name=_(u"Pending")) #default status
        create(QuoteStatus, 2, name=_(u"Accepted"))
        create(QuoteStatus, 3, name=_(u"Rejected"))
        create(QuoteStatus, 4, name=_(u"Created"))

        create(SettlementTerms, 1, name=_(u"30 days")) #default status
        create(SettlementTerms, 2, name=_(u"Cash"))
        create(SettlementTerms, 3, name=_(u"45 days"))
        create(SettlementTerms, 4, name=_(u"60 days"))
        create(SettlementTerms, 5, name=_(u"30 days, end month the 10"))

        create(PaymentTerms, 1, name=_(u"Deposit"), description=_(u"20% deposit will be required"), is_custom=False)

        create(AdditionalInformation, 1, name=_(u"Trainer accreditation"), description=_(u"being certified trainer courses could be supported by your OPCA"), )

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

        ButtonMenuItem.create(pk='billing-generate_invoice_number', model=Invoice, button=generate_invoice_number_button, order=0)

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

        def create_hf_lines(hf_pk, hfi_pref, name, model, include_type=True):
            hf_lines = HeaderFilter.create(pk=hf_pk, name=name, model=model)
            create(HeaderFilterItem, hfi_pref + 'on_the_fly_item',  order=1, name='on_the_fly_item',  title=_(u'On the fly item'), type=HFI_FIELD,    header_filter=hf_lines, has_a_filter=True, editable=True, sortable=True, filter_string="on_the_fly_item__icontains")
            create(HeaderFilterItem, hfi_pref + 'quantity',         order=2, name='quantity',         title=_(u'Quantity'),        type=HFI_FIELD,    header_filter=hf_lines, has_a_filter=True, editable=True, sortable=True, filter_string="quantity__icontains")
            create(HeaderFilterItem, hfi_pref + 'unit_price',       order=3, name='unit_price',       title=_(u'Unit price'),      type=HFI_FIELD,    header_filter=hf_lines, has_a_filter=True, editable=True, sortable=True, filter_string="unit_price__icontains")
            create(HeaderFilterItem, hfi_pref + 'is_paid',          order=4, name='is_paid',          title=_(u'Is paid'),         type=HFI_FIELD,    header_filter=hf_lines, has_a_filter=True, editable=True, sortable=True, filter_string="is_paid__icontains")
            if include_type:
                create(HeaderFilterItem, hfi_pref + 'get_verbose_type', order=5, name='get_verbose_type', title=_(u'Line type'),       type=HFI_FUNCTION, header_filter=hf_lines, has_a_filter=True, editable=True, sortable=False)

        create_hf_lines('billing-hg_lines', 'billing-hfi_line_', _(u"Lines view"), Line)
        create_hf_lines('billing-hg_product_lines', 'billing-hfi_product_line_', _(u"Product lines view"), ProductLine, include_type=False)
        create_hf_lines('billing-hg_service_lines', 'billing-hfi_service_line_', _(u"Service lines view"), ServiceLine, include_type=False)

        for model in (Invoice, CreditNote, Quote, SalesOrder):
            SearchConfigItem.create(model, ['name', 'number', 'status__name'])

        sk = SettingKey.create(pk=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA,
                               description=_(u"Display payment information bloc only on creme managed organisations' detailview"),
                               app_label='billing', type=SettingKey.BOOL
                      )
        SettingValue.objects.create(key=sk, user=None, value=True)
