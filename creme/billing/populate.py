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

from logging import info

from django.utils.translation import ugettext as _

from creme_core.utils import create_or_update as create
from creme_core.models import (RelationType, SearchConfigItem, BlockDetailviewLocation,
                               ButtonMenuItem, HeaderFilterItem, HeaderFilter)
from creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme_core.management.commands.creme_populate import BasePopulator

from creme_config.models import SettingKey, SettingValue

from persons.models import Organisation, Contact

from products.models import Product, Service

from billing.models import *
from billing.constants import *
from billing.blocks import *
from billing.buttons import generate_invoice_number_button


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self, *args, **kwargs):
        billing_entities = [Invoice, Quote, SalesOrder, CreditNote, TemplateBase]
        line_entities = [Line, ProductLine, ServiceLine]
        RelationType.create((REL_SUB_BILL_ISSUED,   _(u"issued by"),    billing_entities),
                            (REL_OBJ_BILL_ISSUED,   _(u"has issued"),   [Organisation]),
                            is_internal=True
                           )
        RelationType.create((REL_SUB_BILL_RECEIVED, _(u"received by"),  billing_entities),
                            (REL_OBJ_BILL_RECEIVED, _(u"has received"), [Organisation, Contact]),
                            is_internal=True
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


        def create_hf_lines(hf_pk, name, model, include_type=True):
            hf = HeaderFilter.create(pk=hf_pk, name=name, model=model)
            items = [HeaderFilterItem.build_4_field(model=model, name='on_the_fly_item'),
                     HeaderFilterItem.build_4_field(model=model, name='quantity'),
                     HeaderFilterItem.build_4_field(model=model, name='unit_price'),
                     HeaderFilterItem.build_4_field(model=model, name='is_paid'),
                    ]

            if include_type:
                items.append(HeaderFilterItem.build_4_functionfield(model.function_fields.get('get_verbose_type')))

            hf.set_items(items)

        create_hf_lines('billing-hg_lines',          _(u"Lines view"),         Line)
        create_hf_lines('billing-hg_product_lines',  _(u"Product lines view"), ProductLine, include_type=False)
        create_hf_lines('billing-hg_service_lines',  _(u"Service lines view"), ServiceLine, include_type=False)

        models = (Invoice, CreditNote, Quote, SalesOrder)

        for model in models:
            BlockDetailviewLocation.create(block_id=product_lines_block.id_,   order=10,  zone=BlockDetailviewLocation.TOP,   model=model)
            BlockDetailviewLocation.create(block_id=service_lines_block.id_,   order=20,  zone=BlockDetailviewLocation.TOP,   model=model)

            BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=model)
            BlockDetailviewLocation.create(block_id=customfields_block.id_,    order=40,  zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=billing_payment_block.id_, order=60,  zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=billing_address_block.id_, order=70,  zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=properties_block.id_,      order=450, zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=relations_block.id_,       order=500, zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=total_block.id_,           order=500, zone=BlockDetailviewLocation.LEFT,  model=model)

            BlockDetailviewLocation.create(block_id=target_block.id_,          order=2,   zone=BlockDetailviewLocation.RIGHT, model=model)
            BlockDetailviewLocation.create(block_id=total_block.id_,           order=3,   zone=BlockDetailviewLocation.RIGHT, model=model)
            BlockDetailviewLocation.create(block_id=history_block.id_,         order=20,  zone=BlockDetailviewLocation.RIGHT, model=model)

        if 'assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail views')

            from assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in models:
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

        BlockDetailviewLocation.create(block_id=payment_information_block.id_,       order=300, zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=received_invoices_block.id_,         order=14,  zone=BlockDetailviewLocation.RIGHT, model=Organisation)
        BlockDetailviewLocation.create(block_id=received_billing_document_block.id_, order=18,  zone=BlockDetailviewLocation.RIGHT, model=Organisation)

        for model in models:
            SearchConfigItem.create(model, ['name', 'number', 'status__name'])

        sk = SettingKey.create(pk=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA,
                               description=_(u"Display payment information bloc only on creme managed organisations' detailview"),
                               app_label='billing', type=SettingKey.BOOL
                              )
        SettingValue.objects.create(key=sk, user=None, value=True)
