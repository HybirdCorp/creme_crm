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
from creme_core.models import RelationType, SearchConfigItem, ButtonMenuItem, HeaderFilterItem, HeaderFilter
from creme_core.management.commands.creme_populate import BasePopulator

from persons.models import Organisation, Contact

from billing.models import *
from billing.constants import *
from billing.buttons import generate_invoice_number_button


class Populator(BasePopulator):
    dependencies = ['creme.creme_core', 'creme.persons']

    def populate(self, *args, **kwargs):
        billing_entities = [Invoice, Quote, SalesOrder, CreditNote, TemplateBase]

        RelationType.create((REL_SUB_BILL_ISSUED,   _(u"issued by"),    billing_entities),
                            (REL_OBJ_BILL_ISSUED,   _(u"has issued"),   [Organisation])
                           )
        RelationType.create((REL_SUB_BILL_RECEIVED, _(u"received by"),  billing_entities),
                            (REL_OBJ_BILL_RECEIVED, _(u"has received"), [Organisation, Contact])
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

        #def create_hf(hf_pk, hfi_pref, name, model):
        def create_hf(hf_pk, name, model):
            hf = HeaderFilter.create(pk=hf_pk, name=name, model=model)
            hf.set_items([HeaderFilterItem.build_4_field(model=model, name='name'),
                          HeaderFilterItem.build_4_field(model=model, name='number'),
                          HeaderFilterItem.build_4_field(model=model, name='issuing_date'),
                          HeaderFilterItem.build_4_field(model=model, name='expiration_date'),
                          HeaderFilterItem.build_4_field(model=model, name='status__name'),
                         ])

        create_hf('billing-hf_invoice',    _(u'Invoice view'),     Invoice)
        create_hf('billing-hf_quote',      _(u'Quote view'),       Quote)
        create_hf('billing-hf_salesorder', _(u'Sales order view'), SalesOrder)
        create_hf('billing-hf_creditnote', _(u'Credit note view'), CreditNote)

        for model in (Invoice, CreditNote, Quote, SalesOrder):
            SearchConfigItem.create(model, ['name', 'number', 'status__name'])

        sk = SettingKey.create(pk=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA,
                               description=_(u"Display payment information bloc only on creme managed organisations' detailview"),
                               app_label='billing', type=SettingKey.BOOL
                      )
        SettingValue.objects.create(key=sk, user=None, value=True)
