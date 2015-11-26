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

#from datetime import date
import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _, pgettext

from creme.creme_core.core.entity_cell import (EntityCellRegularField,
        EntityCellRelation, EntityCellFunctionField)
from creme.creme_core.models import (RelationType, SettingValue, SearchConfigItem,
        ButtonMenuItem, HeaderFilter, EntityFilter, EntityFilterCondition,
        BlockDetailviewLocation, BlockPortalLocation, CustomBlockConfigItem)
from creme.creme_core.blocks import (properties_block, relations_block,
        customfields_block, history_block)
from creme.creme_core.utils import create_if_needed
from creme.creme_core.management.commands.creme_populate import BasePopulator

from creme.persons import get_contact_model, get_organisation_model
#from creme.persons.models import Organisation, Contact

from creme.products import get_product_model, get_service_model
#from creme.products.models import Product, Service

from . import (get_credit_note_model, get_invoice_model, get_quote_model,
        get_sales_order_model, get_template_base_model,
        get_product_line_model, get_service_line_model)
from . import blocks, buttons, constants, setting_keys
#from .models import *
from .models import (InvoiceStatus, QuoteStatus, SalesOrderStatus, CreditNoteStatus,
        SettlementTerms, AdditionalInformation, PaymentTerms)


logger = logging.getLogger(__name__)


CreditNote   = get_credit_note_model()
Invoice      = get_invoice_model()
Quote        = get_quote_model()
SalesOrder   = get_sales_order_model()
TemplateBase = get_template_base_model()

ProductLine = get_product_line_model()
ServiceLine = get_service_line_model()


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_BILL_ISSUED).exists()

        Contact      = get_contact_model()
        Organisation = get_organisation_model()
        Product = get_product_model()
        Service = get_service_model()

        billing_entities = [Invoice, Quote, SalesOrder, CreditNote, TemplateBase]
        line_entities = [ProductLine, ServiceLine] # Line
        RelationType.create((constants.REL_SUB_BILL_ISSUED,   _(u"issued by"),    billing_entities),
                            (constants.REL_OBJ_BILL_ISSUED,   _(u"has issued"),   [Organisation]),
                            is_internal=True
                           )
        rt_sub_bill_received = \
        RelationType.create((constants.REL_SUB_BILL_RECEIVED, _(u"received by"),  billing_entities),
                            (constants.REL_OBJ_BILL_RECEIVED, _(u"has received"), [Organisation, Contact]),
                            is_internal=True
                           )[0]
        RelationType.create((constants.REL_SUB_HAS_LINE, _(u"had the line"),   billing_entities),
                            (constants.REL_OBJ_HAS_LINE, _(u"is the line of"), line_entities),
                            is_internal=True
                           )
        RelationType.create((constants.REL_SUB_LINE_RELATED_ITEM, _(u"has the related item"),   line_entities),
                            (constants.REL_OBJ_LINE_RELATED_ITEM, _(u"is the related item of"), [Product, Service]),
                            is_internal=True
                           )
        RelationType.create((constants.REL_SUB_CREDIT_NOTE_APPLIED, _(u"is used in the billing document"), [CreditNote]),
                            (constants.REL_OBJ_CREDIT_NOTE_APPLIED, _(u"used the credit note"),            [Quote, SalesOrder, Invoice]),
                            is_internal=True
                           )

        if apps.is_installed('creme.activities'):
            logger.info('Activities app is installed => an Invoice/Quote/SalesOrder can be the subject of an Activity')

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT) \
                                .add_subject_ctypes(Invoice, Quote, SalesOrder)



        create_if_needed(PaymentTerms, {'pk': 1}, name=_('Deposit'),
                            description=_(ur'20% deposit will be required'),
                            is_custom=False,
                        )


        # NB: pk=1 + is_custom=False --> default status (used when a quote is converted in invoice for example)
        create_if_needed(SalesOrderStatus, {'pk': 1}, name=pgettext('billing-salesorder', 'Issued'), order=1, is_custom=False) # Default status
        if not already_populated:
            create_if_needed(SalesOrderStatus, {'pk': 2}, name=pgettext('billing-salesorder', 'Accepted'), order=3)
            create_if_needed(SalesOrderStatus, {'pk': 3}, name=pgettext('billing-salesorder', 'Rejected'), order=4)
            create_if_needed(SalesOrderStatus, {'pk': 4}, name=pgettext('billing-salesorder', 'Created'),  order=2)


        def create_invoice_status(pk, name, order, **kwargs):
            create_if_needed(InvoiceStatus, {'pk': pk}, name=name, **kwargs)

        create_invoice_status(1, pgettext('billing-invoice', 'Draft'),      order=1, is_custom=False) # Default status
        create_invoice_status(2, pgettext('billing-invoice', 'To be sent'), order=2, is_custom=False)
        if not already_populated:
            create_invoice_status(3, pgettext('billing-invoice', 'Sent'),            order=3, pending_payment=True)
            create_invoice_status(4, pgettext('billing-invoice', 'Resulted'),        order=5)
            create_invoice_status(5, pgettext('billing-invoice', 'Partly resulted'), order=4, pending_payment=True)
            create_invoice_status(6, _('Collection'),                                order=7)
            create_invoice_status(7, _('Resulted collection'),                       order=6)
            create_invoice_status(8, pgettext('billing-invoice', 'Canceled'),        order=8)


        create_if_needed(CreditNoteStatus, {'pk': 1}, name=pgettext('billing-creditnote', 'Draft'), order=1, is_custom=False)
        if not already_populated:
            create_if_needed(CreditNoteStatus, {'pk': 2}, name=pgettext('billing-creditnote', 'Issued'),      order=2)
            create_if_needed(CreditNoteStatus, {'pk': 3}, name=pgettext('billing-creditnote', 'Consumed'),    order=3)
            create_if_needed(CreditNoteStatus, {'pk': 4}, name=pgettext('billing-creditnote', 'Out of date'), order=4)


        EntityFilter.create(
                'billing-invoices_unpaid', name=_(u"Invoices unpaid"),
                model=Invoice, user='admin',
                conditions=[EntityFilterCondition.build_4_field(
                                    model=Invoice,
                                    operator=EntityFilterCondition.EQUALS,
                                    name='status__pending_payment', values=[True],
                                ),
                           ],
            )
        EntityFilter.create(
                'billing-invoices_unpaid_late', name=_(u"Invoices unpaid and late"),
                model=Invoice, user='admin',
                conditions=[EntityFilterCondition.build_4_field(
                                    model=Invoice,
                                    operator=EntityFilterCondition.EQUALS,
                                    name='status__pending_payment', values=[True],
                                ),
                            EntityFilterCondition.build_4_date(
                                    model=Invoice,
                                    name='expiration_date', date_range='in_past',
                                ),
                           ],
            )
        current_year_invoice_filter = EntityFilter.create(
                'billing-current_year_invoices', name=_(u"Current year invoices"),
                model=Invoice, user='admin',
                conditions=[EntityFilterCondition.build_4_date(
                                    model=Invoice,
                                    name='issuing_date', date_range='current_year',
                                ),
                           ],
            )
        current_year_unpaid_invoice_filter = EntityFilter.create(
                'billing-current_year_unpaid_invoices',
                name=_(u"Current year and unpaid invoices"),
                model=Invoice, user='admin',
                conditions=[EntityFilterCondition.build_4_date(
                                    model=Invoice,
                                    name='issuing_date', date_range='current_year',
                                ),
                            EntityFilterCondition.build_4_field(
                                    model=Invoice,
                                    operator=EntityFilterCondition.EQUALS,
                                    name='status__pending_payment', values=[True],
                                ),
                           ],
            )


        def create_hf(hf_pk, name, model, status=True):
            HeaderFilter.create(pk=hf_pk, name=name, model=model,
                                cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                            EntityCellRelation(rtype=rt_sub_bill_received),
                                            (EntityCellRegularField, {'name': 'number'}),
                                            (EntityCellRegularField, {'name': 'status'}) if status else None,
                                            (EntityCellRegularField, {'name': 'total_no_vat'}),
                                            (EntityCellRegularField, {'name': 'issuing_date'}),
                                            (EntityCellRegularField, {'name': 'expiration_date'}),
                                           ],
                               )

        create_hf(constants.DEFAULT_HFILTER_INVOICE,  _(u'Invoice view'),     Invoice)
        create_hf(constants.DEFAULT_HFILTER_QUOTE,    _(u'Quote view'),       Quote)
        create_hf(constants.DEFAULT_HFILTER_ORDER,    _(u'Sales order view'), SalesOrder)
        create_hf(constants.DEFAULT_HFILTER_CNOTE,    _(u'Credit note view'), CreditNote)
        create_hf(constants.DEFAULT_HFILTER_TEMPLATE, _(u'Template view'),    TemplateBase, status=False)


#        def create_hf_lines(hf_pk, name, model, include_type=True):
        def create_hf_lines(hf_pk, name, model):
            cells_desc = [EntityCellRegularField.build(model=model, name='on_the_fly_item'),
                          EntityCellRegularField.build(model=model, name='quantity'),
                          EntityCellRegularField.build(model=model, name='unit_price'),
                          #EntityCellRegularField.build(model=model, name='is_paid'),
                         ]

#            if include_type:
#                cells_desc.append(EntityCellFunctionField.build(model, 'get_verbose_type'))

            HeaderFilter.create(pk=hf_pk, name=name, model=model, cells_desc=cells_desc)

#        create_hf_lines('billing-hg_lines',         _(u"Lines view"),         Line)
        create_hf_lines('billing-hg_product_lines', _(u"Product lines view"), ProductLine) #include_type=False
        create_hf_lines('billing-hg_service_lines', _(u"Service lines view"), ServiceLine) #include_type=False


        for model in (Invoice, CreditNote, Quote, SalesOrder):
            SearchConfigItem.create_if_needed(model, ['name', 'number', 'status__name'])

        for model in (ProductLine, ServiceLine): #Line
            SearchConfigItem.create_if_needed(model, [], disabled=True)

        SettingValue.create_if_needed(key=setting_keys.payment_info_key, user=None, value=True)


        if not already_populated:
            create_if_needed(QuoteStatus, {'pk': 1}, name=pgettext('billing-quote', "Pending"),  order=2) # Default status
            create_if_needed(QuoteStatus, {'pk': 2}, name=pgettext('billing-quote', "Accepted"), order=3, won=True)
            create_if_needed(QuoteStatus, {'pk': 3}, name=pgettext('billing-quote', "Rejected"), order=4)
            create_if_needed(QuoteStatus, {'pk': 4}, name=pgettext('billing-quote', "Created"),  order=1)


            create_if_needed(SettlementTerms, {'pk': 1}, name=_('30 days'))
            create_if_needed(SettlementTerms, {'pk': 2}, name=_('Cash'))
            create_if_needed(SettlementTerms, {'pk': 3}, name=_('45 days'))
            create_if_needed(SettlementTerms, {'pk': 4}, name=_('60 days'))
            create_if_needed(SettlementTerms, {'pk': 5}, name=_('30 days, end month the 10'))


            create_if_needed(AdditionalInformation, {'pk': 1}, name=_('Trainer accreditation'),
                             description=_('being certified trainer courses could be supported by your OPCA')
                            )


            create_bmi = ButtonMenuItem.create_if_needed
            create_bmi(pk='billing-generate_invoice_number', model=Invoice, button=buttons.generate_invoice_number_button, order=0)

            create_bmi(pk='billing-quote_orga_button',      model=Organisation, button=buttons.add_related_quote,      order=100)
            create_bmi(pk='billing-salesorder_orga_button', model=Organisation, button=buttons.add_related_salesorder, order=101)
            create_bmi(pk='billing-invoice_orga_button',    model=Organisation, button=buttons.add_related_invoice,    order=102)

            create_bmi(pk='billing-quote_contact_button',      model=Contact, button=buttons.add_related_quote,      order=100)
            create_bmi(pk='billing-salesorder_contact_button', model=Contact, button=buttons.add_related_salesorder, order=101)
            create_bmi(pk='billing-invoice_contact_button',    model=Contact, button=buttons.add_related_invoice,    order=102)


            get_ct = ContentType.objects.get_for_model
            create_cbci = CustomBlockConfigItem.objects.create
            build_cell = EntityCellRegularField.build

            def build_common_cells(model):
                return [build_cell(model, 'created'),
                        build_cell(model, 'modified'),
                        build_cell(model, 'user'),
                        build_cell(model, 'name'),
                        build_cell(model, 'number'),
                        build_cell(model, 'issuing_date'),
                        build_cell(model, 'expiration_date'),
                        build_cell(model, 'discount'),
                        build_cell(model, 'comment'),
                        build_cell(model, 'additional_info'),
                        build_cell(model, 'payment_terms'),
                        build_cell(model, 'currency'),
                       ]

            cbci_invoice = create_cbci(id='billing-invoice_info',
                                       name=_(u'Invoice information'),
                                       content_type=get_ct(Invoice),
                                       cells=build_common_cells(Invoice) +
                                             [build_cell(Invoice, 'status'),
                                              build_cell(Invoice, 'payment_type'),
                                             ],
                                      )
            cbci_c_note   = create_cbci(id='billing-creditnote_info',
                                       name=_(u'Credit note information'),
                                       content_type=get_ct(CreditNote),
                                       cells=build_common_cells(CreditNote) +
                                             [build_cell(CreditNote, 'status')],
                                      )
            cbci_quote   = create_cbci(id='billing-quote_info',
                                       name=_(u'Quote information'),
                                       content_type=get_ct(Quote),
                                       cells=build_common_cells(Quote) +
                                             [build_cell(Quote, 'status'),
                                              build_cell(Quote, 'acceptation_date'),
                                             ],
                                      )
            cbci_s_order = create_cbci(id='billing-salesorder_info',
                                       name=_(u'Salesorder information'),
                                       content_type=get_ct(SalesOrder),
                                       cells=build_common_cells(SalesOrder) +
                                             [build_cell(SalesOrder, 'status')],
                                      )
            cbci_tbase   = create_cbci(id='billing-templatebase_info',
                                       name=pgettext('billing', u'Template information'),
                                       content_type=get_ct(TemplateBase),
                                       cells=build_common_cells(TemplateBase) +
                                             [EntityCellFunctionField.build(TemplateBase, 'get_verbose_status')],
                                      )

            models_4_blocks = [(Invoice,      cbci_invoice, True), # Boolean -> insert CreditNote block
                               (CreditNote,   cbci_c_note,  False),
                               (Quote,        cbci_quote,   True),
                               (SalesOrder,   cbci_s_order, True),
                               (TemplateBase, cbci_tbase,   False),
                              ]
            create_bdl = BlockDetailviewLocation.create
            TOP = BlockDetailviewLocation.TOP
            LEFT = BlockDetailviewLocation.LEFT
            RIGHT = BlockDetailviewLocation.RIGHT

            for model, cbci, has_credit_notes in models_4_blocks:
                create_bdl(block_id=blocks.product_lines_block.id_,   order=10,  zone=TOP,   model=model)
                create_bdl(block_id=blocks.service_lines_block.id_,   order=20,  zone=TOP,   model=model)

                if has_credit_notes:
                    create_bdl(block_id=blocks.credit_note_block.id_, order=30,  zone=TOP,   model=model)

#                BlockDetailviewLocation.create_4_model_block(order=5, zone=LEFT, model=model)
                create_bdl(block_id=cbci.generate_id(),               order=5,   zone=LEFT,  model=model)
                create_bdl(block_id=customfields_block.id_,           order=40,  zone=LEFT,  model=model)
                create_bdl(block_id=blocks.billing_payment_block.id_, order=60,  zone=LEFT,  model=model)
                create_bdl(block_id=blocks.billing_address_block.id_, order=70,  zone=LEFT,  model=model)
                create_bdl(block_id=properties_block.id_,             order=450, zone=LEFT,  model=model)
                create_bdl(block_id=relations_block.id_,              order=500, zone=LEFT,  model=model)

                create_bdl(block_id=blocks.target_block.id_,          order=2,   zone=RIGHT, model=model)
                create_bdl(block_id=blocks.total_block.id_,           order=3,   zone=RIGHT, model=model)
                create_bdl(block_id=history_block.id_,                order=20,  zone=RIGHT, model=model)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.blocks import alerts_block, memos_block, todos_block, messages_block

                for t in models_4_blocks:
                    model = t[0]
                    create_bdl(block_id=todos_block.id_,    order=100, zone=RIGHT, model=model)
                    create_bdl(block_id=memos_block.id_,    order=200, zone=RIGHT, model=model)
                    create_bdl(block_id=alerts_block.id_,   order=300, zone=RIGHT, model=model)
                    create_bdl(block_id=messages_block.id_, order=400, zone=RIGHT, model=model)

            create_bdl(block_id=blocks.payment_information_block.id_, order=300, zone=LEFT,  model=Organisation)
            create_bdl(block_id=blocks.received_invoices_block.id_,   order=14,  zone=RIGHT, model=Organisation)
#            create_bdl(block_id=blocks.received_billing_document_block.id_, order=18,  zone=RIGHT, model=Organisation)
            create_bdl(block_id=blocks.received_quotes_block.id_,     order=18,  zone=RIGHT, model=Organisation)


            if apps.is_installed('creme.reports'):
                logger.info('Reports app is installed => we create 2 billing reports, with 3 graphs, and related blocks in home')
                self.create_reports(rt_sub_bill_received,
                                    current_year_invoice_filter,
                                    current_year_unpaid_invoice_filter,
                                   )

    def create_reports(self, rt_sub_bill_received, current_year_invoice_filter, current_year_unpaid_invoice_filter):
        from functools import partial

        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType

        from creme.reports.constants import RFT_FIELD, RFT_RELATION, RGT_FK, RGT_MONTH
        from creme.reports.models import Report, Field, ReportGraph


#        admin = get_user_model().objects.get(pk=1)
        admin = get_user_model().objects.get_admin()

        def create_report_columns(report):
            create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
            create_field(name='name',                  order=1)
            create_field(name=rt_sub_bill_received.id, order=2, type=RFT_RELATION)
            create_field(name='number',                order=3)
            create_field(name='status',                order=4)
            create_field(name='total_no_vat',          order=5)
            create_field(name='issuing_date',          order=6)
            create_field(name='expiration_date',       order=7)

        create_report = partial(Report.objects.create, user=admin,
                                ct=ContentType.objects.get_for_model(Invoice),
                               )
        create_graph = partial(ReportGraph.objects.create, user=admin)

        # Create current year invoices report ----------------------------------
        invoices_report1 = create_report(name=_(u'All invoices of the current year'),
                                         filter=current_year_invoice_filter,
                                        )
        create_report_columns(invoices_report1)

        rgraph1 = create_graph(name=_(u"Sum of current year invoices total without taxes / month"),
                               report=invoices_report1,
                               abscissa='issuing_date', ordinate='total_no_vat__sum',
                               type=RGT_MONTH, is_count=False,
                              )
        create_graph(name=_(u"Sum of current year invoices total without taxes / invoices status"),
                     report=invoices_report1,
                     abscissa='status', ordinate='total_no_vat__sum',
                     type=RGT_FK, is_count=False,
                    )
        ibci = rgraph1.create_instance_block_config_item()

        BlockPortalLocation.create(app_name='creme_core', block_id=ibci.block_id, order=1)

        # Create current year and unpaid invoices report -----------------------
        invoices_report2 = create_report(name=_(u'Invoices unpaid of the current year'),
                                         filter=current_year_unpaid_invoice_filter,
                                        )
        create_report_columns(invoices_report2)

        rgraph = create_graph(name=_(u"Sum of current year and unpaid invoices total without taxes / month"),
                              report=invoices_report2,
                              abscissa='issuing_date', ordinate='total_no_vat__sum',
                              type=RGT_MONTH, is_count=False,
                             )
        ibci = rgraph.create_instance_block_config_item()

        BlockPortalLocation.create(app_name='creme_core', block_id=ibci.block_id, order=2)
