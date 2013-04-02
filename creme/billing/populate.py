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

#from datetime import date
from decimal import Decimal
from logging import info

from django.utils.translation import ugettext as _, pgettext

from creme.creme_core.models import (RelationType, SearchConfigItem, BlockDetailviewLocation,
                               ButtonMenuItem, HeaderFilterItem, HeaderFilter,
                               BlockPortalLocation, EntityFilterCondition, EntityFilter)
from creme.creme_core.blocks import properties_block, relations_block, customfields_block, history_block
from creme.creme_core.utils import create_if_needed
from creme.creme_core.management.commands.creme_populate import BasePopulator

from creme.creme_config.models import SettingKey, SettingValue

from creme.persons.models import Organisation, Contact

from creme.products.models import Product, Service

from .models import *
from .constants import *
from .blocks import *
from .buttons import *


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate(self, *args, **kwargs):
        billing_entities = [Invoice, Quote, SalesOrder, CreditNote, TemplateBase]
        line_entities = [Line, ProductLine, ServiceLine]
        RelationType.create((REL_SUB_BILL_ISSUED,   _(u"issued by"),    billing_entities),
                            (REL_OBJ_BILL_ISSUED,   _(u"has issued"),   [Organisation]),
                            is_internal=True
                           )
        rt_sub_bill_received, rt_obj_bill_received = \
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
        RelationType.create((REL_SUB_CREDIT_NOTE_APPLIED, _(u"is used in the billing document"), [CreditNote]),
                            (REL_OBJ_CREDIT_NOTE_APPLIED, _(u"used the credit note"),            [Quote, SalesOrder, Invoice]),
                            is_internal=True
                           )


        existing_vats = frozenset(Vat.objects.values_list('value', flat=True))
        if not existing_vats:
            values = set(Decimal(value) for value in ['0.0', '5.50', '7.0', '19.60'])
            values.add(DEFAULT_VAT)

            create_vat = Vat.objects.create
            for value in values:
                create_vat(value=value, is_default=(value == DEFAULT_VAT), is_custom=False)

        #NB: pk=1 --> default status (used when a quote is converted in invoice for example)
        create_if_needed(QuoteStatus, {'pk': 1}, name=pgettext('billing-quote', "Pending"),  order=2) #default status
        create_if_needed(QuoteStatus, {'pk': 2}, name=pgettext('billing-quote', "Accepted"), order=3)
        create_if_needed(QuoteStatus, {'pk': 3}, name=pgettext('billing-quote', "Rejected"), order=4)
        create_if_needed(QuoteStatus, {'pk': 4}, name=pgettext('billing-quote', "Created"),  order=1)

        create_if_needed(SettlementTerms, {'pk': 1}, name=_(u"30 days")) #default status
        create_if_needed(SettlementTerms, {'pk': 2}, name=_(u"Cash"))
        create_if_needed(SettlementTerms, {'pk': 3}, name=_(u"45 days"))
        create_if_needed(SettlementTerms, {'pk': 4}, name=_(u"60 days"))
        create_if_needed(SettlementTerms, {'pk': 5}, name=_(u"30 days, end month the 10"))

        create_if_needed(PaymentTerms, {'pk': 1}, name=_(u"Deposit"), description=_(u"20% deposit will be required"), is_custom=False)

        create_if_needed(AdditionalInformation, {'pk': 1},
                         name=_(u"Trainer accreditation"),
                         description=_(u"being certified trainer courses could be supported by your OPCA")
                        )

        create_if_needed(SalesOrderStatus, {'pk': 1}, name=pgettext('billing-salesorder', 'Issued'),   is_custom=False, order=1) #default status
        create_if_needed(SalesOrderStatus, {'pk': 2}, name=pgettext('billing-salesorder', 'Accepted'), is_custom=True,  order=3)
        create_if_needed(SalesOrderStatus, {'pk': 3}, name=pgettext('billing-salesorder', 'Rejected'), is_custom=True,  order=4)
        create_if_needed(SalesOrderStatus, {'pk': 4}, name=pgettext('billing-salesorder', 'Created'),  is_custom=True,  order=2)


        def create_invoice_status(pk, name, order, is_custom=True):
            istatus = create_if_needed(InvoiceStatus, {'pk': pk}, name=name, is_custom=is_custom, order=order)
            return istatus if istatus.name == name else None

        create_invoice_status(1, pgettext('billing-invoice', 'Draft'),           order=1, is_custom=False) #default status
        create_invoice_status(2, pgettext('billing-invoice', 'To be sent'),      order=2, is_custom=False)
        create_invoice_status(3, pgettext('billing-invoice', 'Sent'),            order=3)
        resulted = \
        create_invoice_status(4, pgettext('billing-invoice', 'Resulted'),        order=5)
        create_invoice_status(5, pgettext('billing-invoice', 'Partly resulted'), order=4)
        create_invoice_status(6, _('Collection'),                                order=7)
        resulted_collection = \
        create_invoice_status(7, _('Resulted collection'),                       order=6)
        create_invoice_status(8, pgettext('billing-invoice', 'Canceled'),        order=8)


        create_if_needed(CreditNoteStatus, {'pk': 1}, name=pgettext('billing-creditnote', 'Draft'),       is_custom=False, order=1)
        create_if_needed(CreditNoteStatus, {'pk': 2}, name=pgettext('billing-creditnote', 'Issued'),      is_custom=True,  order=2)
        create_if_needed(CreditNoteStatus, {'pk': 3}, name=pgettext('billing-creditnote', 'Consumed'),    is_custom=True,  order=3)
        create_if_needed(CreditNoteStatus, {'pk': 4}, name=pgettext('billing-creditnote', 'Out of date'), is_custom=True,  order=4)

        ButtonMenuItem.create_if_needed(pk='billing-generate_invoice_number', model=Invoice, button=generate_invoice_number_button, order=0)

        def create_hf(hf_pk, name, model):
            hf = HeaderFilter.create(pk=hf_pk, name=name, model=model)
            hf.set_items([HeaderFilterItem.build_4_field(model=model, name='name'),
                          HeaderFilterItem.build_4_relation(rtype=rt_sub_bill_received),
                          HeaderFilterItem.build_4_field(model=model, name='number'),
                          HeaderFilterItem.build_4_field(model=model, name='status'), #status__name
                          HeaderFilterItem.build_4_field(model=model, name='total_no_vat'),
                          HeaderFilterItem.build_4_field(model=model, name='issuing_date'),
                          HeaderFilterItem.build_4_field(model=model, name='expiration_date'),
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
#                     HeaderFilterItem.build_4_field(model=model, name='is_paid'),
                    ]

            if include_type:
                items.append(HeaderFilterItem.build_4_functionfield(model.function_fields.get('get_verbose_type')))

            hf.set_items(items)

        create_hf_lines('billing-hg_lines',         _(u"Lines view"),         Line)
        create_hf_lines('billing-hg_product_lines', _(u"Product lines view"), ProductLine, include_type=False)
        create_hf_lines('billing-hg_service_lines', _(u"Service lines view"), ServiceLine, include_type=False)

        if resulted and resulted_collection:
            efilter = EntityFilter.create('billing-invoices_unpaid', name=_(u"Invoices unpaid"), model=Invoice)
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=Invoice, operator=EntityFilterCondition.EQUALS_NOT, name='status', values=[resulted.pk, resulted_collection.pk])])

            efilter = EntityFilter.create('billing-invoices_unpaid_late', name=_(u"Invoices unpaid and late"), model=Invoice)
            efilter.set_conditions([EntityFilterCondition.build_4_field(model=Invoice, operator=EntityFilterCondition.EQUALS_NOT, name='status', values=[resulted.pk, resulted_collection.pk]),
                                    EntityFilterCondition.build_4_date(model=Invoice, name='expiration_date', date_range='in_past'),
                                   ])

        create_bmi = ButtonMenuItem.create_if_needed
        create_bmi(pk='billing-quote_orga_button',      model=Organisation, button=add_related_quote,      order=100)
        create_bmi(pk='billing-salesorder_orga_button', model=Organisation, button=add_related_salesorder, order=101)
        create_bmi(pk='billing-invoice_orga_button',    model=Organisation, button=add_related_invoice,    order=102)

        create_bmi(pk='billing-quote_contact_button',       model=Contact, button=add_related_quote,      order=100)
        create_bmi(pk='billing-salesorder_contact_button',  model=Contact, button=add_related_salesorder, order=101)
        create_bmi(pk='billing-invoice_contact_button',     model=Contact, button=add_related_invoice,    order=102)

        models = (Invoice, CreditNote, Quote, SalesOrder)

        for model in models:
            BlockDetailviewLocation.create(block_id=product_lines_block.id_,   order=10,  zone=BlockDetailviewLocation.TOP,   model=model)
            BlockDetailviewLocation.create(block_id=service_lines_block.id_,   order=20,  zone=BlockDetailviewLocation.TOP,   model=model)
            if model is not CreditNote:
                BlockDetailviewLocation.create(block_id=credit_note_block.id_,     order=30,  zone=BlockDetailviewLocation.TOP,   model=model)

            BlockDetailviewLocation.create_4_model_block(order=5, zone=BlockDetailviewLocation.LEFT, model=model)
            BlockDetailviewLocation.create(block_id=customfields_block.id_,    order=40,  zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=billing_payment_block.id_, order=60,  zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=billing_address_block.id_, order=70,  zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=properties_block.id_,      order=450, zone=BlockDetailviewLocation.LEFT,  model=model)
            BlockDetailviewLocation.create(block_id=relations_block.id_,       order=500, zone=BlockDetailviewLocation.LEFT,  model=model)

            BlockDetailviewLocation.create(block_id=target_block.id_,          order=2,   zone=BlockDetailviewLocation.RIGHT, model=model)
            BlockDetailviewLocation.create(block_id=total_block.id_,           order=3,   zone=BlockDetailviewLocation.RIGHT, model=model)
            BlockDetailviewLocation.create(block_id=history_block.id_,         order=20,  zone=BlockDetailviewLocation.RIGHT, model=model)

        if 'creme.assistants' in settings.INSTALLED_APPS:
            info('Assistants app is installed => we use the assistants blocks on detail views')

            from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

            for model in models:
                BlockDetailviewLocation.create(block_id=todos_block.id_,    order=100, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=memos_block.id_,    order=200, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=alerts_block.id_,   order=300, zone=BlockDetailviewLocation.RIGHT, model=model)
                BlockDetailviewLocation.create(block_id=messages_block.id_, order=400, zone=BlockDetailviewLocation.RIGHT, model=model)

        BlockDetailviewLocation.create(block_id=payment_information_block.id_,       order=300, zone=BlockDetailviewLocation.LEFT,  model=Organisation)
        BlockDetailviewLocation.create(block_id=received_invoices_block.id_,         order=14,  zone=BlockDetailviewLocation.RIGHT, model=Organisation)
        BlockDetailviewLocation.create(block_id=received_billing_document_block.id_, order=18,  zone=BlockDetailviewLocation.RIGHT, model=Organisation)

        for model in models:
            SearchConfigItem.create_if_needed(model, ['name', 'number', 'status__name'])

        sk = SettingKey.create(pk=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA,
                               description=_(u"Display payment information block only on the detailview of organisations managed by Creme"),
                               app_label='billing', type=SettingKey.BOOL
                              )
        SettingValue.create_if_needed(key=sk, user=None, value=True)

        if 'creme.reports' in settings.INSTALLED_APPS:
            info('Reports app is installed => we create 2 billing reports, with 3 graphs, and related blocks in home')
            self.create_reports(rt_sub_bill_received, resulted, resulted_collection)

    def create_reports(self, rt_sub_bill_received, resulted, resulted_collection):
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import User

        from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
        from creme.creme_core.utils.meta import get_verbose_field_name

        from creme.reports.models import Report, Field, ReportGraph
        from creme.reports.models.graph import RGT_FK, RGT_MONTH

        if not (resulted and resulted_collection):
            print "Invoice status 'Resulted' and/or 'Resulted collection' have change => do not create reports 'All invoices of the current year' and 'Invoices unpaid of the current year'"
            return

        invoice_ct = ContentType.objects.get_for_model(Invoice)
        admin = User.objects.get(pk=1)

        current_year_invoice_filter = EntityFilter.create('billing-current_year_invoices', _(u"Current year invoices"), Invoice)
        current_year_invoice_filter.set_conditions([EntityFilterCondition.build_4_date(model=Invoice, name='issuing_date', date_range='current_year')])

        current_year_unpaid_invoice_filter = EntityFilter.create('billing-current_year_unpaid_invoices', _(u"Current year and unpaid invoices"), Invoice)
        current_year_unpaid_invoice_filter.set_conditions([EntityFilterCondition.build_4_date(model=Invoice, name='issuing_date', date_range='current_year'),
                                                           EntityFilterCondition.build_4_field(model=Invoice, operator=EntityFilterCondition.EQUALS_NOT, name='status', values=[resulted.pk, resulted_collection.pk]),
                                                          ])

        def create_report_columns():
            create_field = Field.objects.create
            return [create_field(name='name',                  title=get_verbose_field_name(Invoice, 'name'),            order=1, type=HFI_FIELD),
                    create_field(name=rt_sub_bill_received.id, title=unicode(rt_sub_bill_received),                      order=2, type=HFI_RELATION),
                    create_field(name='number',                title=get_verbose_field_name(Invoice, 'number'),          order=3, type=HFI_FIELD),
                    create_field(name='status',                title=get_verbose_field_name(Invoice, 'status'),          order=4, type=HFI_FIELD),
                    create_field(name='total_no_vat',          title=get_verbose_field_name(Invoice, 'total_no_vat'),    order=5, type=HFI_FIELD),
                    create_field(name='issuing_date',          title=get_verbose_field_name(Invoice, 'issuing_date'),    order=6, type=HFI_FIELD),
                    create_field(name='expiration_date',       title=get_verbose_field_name(Invoice, 'expiration_date'), order=7, type=HFI_FIELD),
                   ]

        create_graph = ReportGraph.objects.create

        #Create current year invoices report -----------------------------------
        report_name = _(u"All invoices of the current year")
        try:
            Report.objects.get(name=report_name, ct=invoice_ct)
        except:
            invoices_report = Report.objects.create(name=report_name, ct=invoice_ct, filter=current_year_invoice_filter, user=admin)
            invoices_report.columns = create_report_columns()

            rgraph1 = create_graph(name=_(u"Sum of current year invoices total without taxes / month"), report=invoices_report, abscissa='issuing_date', ordinate='total_no_vat__sum', type=RGT_MONTH, is_count=False, user=admin)
            create_graph(name=_(u"Sum of current year invoices total without taxes / invoices status"), report=invoices_report, abscissa='status',       ordinate='total_no_vat__sum', type=RGT_FK,    is_count=False, user=admin)
            ibci = rgraph1.create_instance_block_config_item()

            BlockPortalLocation.create(app_name='creme_core', block_id=ibci.block_id, order=1)
        else:
            print "The report 'Invoices of the current year' already exists"

        #Create current year and unpaid invoices report ------------------------
        report_name = _(u"Invoices unpaid of the current year")
        try:
            Report.objects.get(name=report_name, ct=invoice_ct)
        except:
            invoices_report = Report.objects.create(name=report_name, ct=invoice_ct, filter=current_year_unpaid_invoice_filter, user=admin)
            invoices_report.columns = create_report_columns()

            rgraph = create_graph(name=_(u"Sum of current year and unpaid invoices total without taxes / month"),
                                  report=invoices_report, user=admin,
                                  abscissa='issuing_date', ordinate='total_no_vat__sum', type=RGT_MONTH, is_count=False
                                 )
            ibci = rgraph.create_instance_block_config_item()

            BlockPortalLocation.create(app_name='creme_core', block_id=ibci.block_id, order=2)
        else:
            print "The report 'Invoices unpaid of the current year' already exists"
