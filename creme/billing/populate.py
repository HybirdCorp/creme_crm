# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

import logging

from django.apps import apps
from django.utils.translation import gettext as _, pgettext

from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
    EntityCellFunctionField,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    RelationType,
    SettingValue,
    SearchConfigItem,
    ButtonMenuItem,
    HeaderFilter,
    EntityFilter,  # EntityFilterCondition
    BrickDetailviewLocation, BrickHomeLocation, CustomBrickConfigItem,
)
from creme.creme_core.utils import create_if_needed

from creme import persons, products, billing

from . import bricks, buttons, constants, setting_keys
from .core import BILLING_MODELS
from .models import (
    InvoiceStatus, QuoteStatus, SalesOrderStatus, CreditNoteStatus,
    SettlementTerms, AdditionalInformation, PaymentTerms,
)
from .registry import lines_registry

logger = logging.getLogger(__name__)

CreditNote   = billing.get_credit_note_model()
Invoice      = billing.get_invoice_model()
Quote        = billing.get_quote_model()
SalesOrder   = billing.get_sales_order_model()
TemplateBase = billing.get_template_base_model()

ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities']

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_BILL_ISSUED).exists()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()
        Product = products.get_product_model()
        Service = products.get_service_model()

        # ---------------------------
        # line_entities = [ProductLine, ServiceLine]
        line_entities = [*lines_registry]
        RelationType.create((constants.REL_SUB_BILL_ISSUED, _('issued by'),  BILLING_MODELS),
                            (constants.REL_OBJ_BILL_ISSUED, _('has issued'), [Organisation]),
                            is_internal=True,
                            minimal_display=(False, True),
                           )
        rt_sub_bill_received = \
        RelationType.create((constants.REL_SUB_BILL_RECEIVED, _('received by'),  BILLING_MODELS),
                            (constants.REL_OBJ_BILL_RECEIVED, _('has received'), [Organisation, Contact]),
                            is_internal=True,
                            minimal_display=(False, True),
                           )[0]
        RelationType.create((constants.REL_SUB_HAS_LINE, _('had the line'),   BILLING_MODELS),
                            (constants.REL_OBJ_HAS_LINE, _('is the line of'), line_entities),
                            is_internal=True,
                            minimal_display=(True, True),
                           )
        RelationType.create((constants.REL_SUB_LINE_RELATED_ITEM, _('has the related item'),   line_entities),
                            (constants.REL_OBJ_LINE_RELATED_ITEM, _('is the related item of'), [Product, Service]),
                            is_internal=True,
                           )
        RelationType.create((constants.REL_SUB_CREDIT_NOTE_APPLIED, _('is used in the billing document'), [CreditNote]),
                            (constants.REL_OBJ_CREDIT_NOTE_APPLIED, _('used the credit note'),            [Quote, SalesOrder, Invoice]),
                            is_internal=True,
                            minimal_display=(True, True),
                           )

        if apps.is_installed('creme.activities'):
            logger.info('Activities app is installed => an Invoice/Quote/SalesOrder can be the subject of an Activity')

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(pk=REL_SUB_ACTIVITY_SUBJECT) \
                                .add_subject_ctypes(Invoice, Quote, SalesOrder)

        # ---------------------------
        create_if_needed(PaymentTerms, {'pk': 1}, name=_('Deposit'),
                         description=_(r'20% deposit will be required'),
                         is_custom=False,
                        )

        # ---------------------------
        # NB: pk=1 + is_custom=False --> default status (used when a quote is converted in invoice for example)
        create_if_needed(SalesOrderStatus, {'pk': 1}, name=pgettext('billing-salesorder', 'Issued'), order=1, is_custom=False) # Default status
        if not already_populated:
            create_if_needed(SalesOrderStatus, {'pk': 2}, name=pgettext('billing-salesorder', 'Accepted'), order=3)
            create_if_needed(SalesOrderStatus, {'pk': 3}, name=pgettext('billing-salesorder', 'Rejected'), order=4)
            create_if_needed(SalesOrderStatus, {'pk': 4}, name=pgettext('billing-salesorder', 'Created'),  order=2)

        # ---------------------------
        def create_invoice_status(pk, name, order, **kwargs):
            create_if_needed(InvoiceStatus, {'pk': pk}, name=name, **kwargs)

        create_invoice_status(1, pgettext('billing-invoice', 'Draft'),      order=1, is_custom=False)  # Default status
        create_invoice_status(2, pgettext('billing-invoice', 'To be sent'), order=2, is_custom=False)
        if not already_populated:
            create_invoice_status(3, pgettext('billing-invoice', 'Sent'),            order=3, pending_payment=True)
            create_invoice_status(4, pgettext('billing-invoice', 'Resulted'),        order=5)
            create_invoice_status(5, pgettext('billing-invoice', 'Partly resulted'), order=4, pending_payment=True)
            create_invoice_status(6, _('Collection'),                                order=7)
            create_invoice_status(7, _('Resulted collection'),                       order=6)
            create_invoice_status(8, pgettext('billing-invoice', 'Canceled'),        order=8)

        # ---------------------------
        create_if_needed(CreditNoteStatus, {'pk': 1}, name=pgettext('billing-creditnote', 'Draft'), order=1, is_custom=False)
        if not already_populated:
            create_if_needed(CreditNoteStatus, {'pk': 2}, name=pgettext('billing-creditnote', 'Issued'),      order=2)
            create_if_needed(CreditNoteStatus, {'pk': 3}, name=pgettext('billing-creditnote', 'Consumed'),    order=3)
            create_if_needed(CreditNoteStatus, {'pk': 4}, name=pgettext('billing-creditnote', 'Out of date'), order=4)

        # ---------------------------
        EntityFilter.create(
            'billing-invoices_unpaid', name=_('Invoices unpaid'),
            model=Invoice, user='admin',
            conditions=[
                # EntityFilterCondition.build_4_field(
                #     model=Invoice,
                #     operator=EntityFilterCondition.EQUALS,
                #     name='status__pending_payment', values=[True],
                # ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    operator=operators.EqualsOperator,
                    field_name='status__pending_payment',
                    values=[True],
                ),
            ],
        )
        EntityFilter.create(
            'billing-invoices_unpaid_late', name=_('Invoices unpaid and late'),
            model=Invoice, user='admin',
            conditions=[
                # EntityFilterCondition.build_4_field(
                #     model=Invoice,
                #     operator=EntityFilterCondition.EQUALS,
                #     name='status__pending_payment', values=[True],
                # ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    operator=operators.EqualsOperator,
                    field_name='status__pending_payment',
                    values=[True],
                ),
                # EntityFilterCondition.build_4_date(
                #     model=Invoice,
                #     name='expiration_date', date_range='in_past',
                # ),
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    field_name='expiration_date',
                    date_range='in_past',
                ),
            ],
        )
        current_year_invoice_filter = EntityFilter.create(
            'billing-current_year_invoices', name=_('Current year invoices'),
            model=Invoice, user='admin',
            conditions=[
                # EntityFilterCondition.build_4_date(
                #     model=Invoice,
                #     name='issuing_date', date_range='current_year',
                # ),
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    field_name='issuing_date',
                    date_range='current_year',
                ),
            ],
        )
        current_year_unpaid_invoice_filter = EntityFilter.create(
            'billing-current_year_unpaid_invoices',
            name=_('Current year and unpaid invoices'),
            model=Invoice, user='admin',
            conditions=[
                # EntityFilterCondition.build_4_date(
                #     model=Invoice,
                #     name='issuing_date', date_range='current_year',
                # ),
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    field_name='issuing_date',
                    date_range='current_year',
                ),
                # EntityFilterCondition.build_4_field(
                #     model=Invoice,
                #     operator=EntityFilterCondition.EQUALS,
                #     name='status__pending_payment', values=[True],
                # ),
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    operator=operators.EqualsOperator,
                    field_name='status__pending_payment',
                    values=[True],
                ),
            ],
        )

        # ---------------------------
        def create_hf(hf_pk, name, model, status=True):
            HeaderFilter.create(pk=hf_pk, name=name, model=model,
                                cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                            EntityCellRelation(model=model, rtype=rt_sub_bill_received),
                                            (EntityCellRegularField, {'name': 'number'}),
                                            (EntityCellRegularField, {'name': 'status'}) if status else None,
                                            (EntityCellRegularField, {'name': 'total_no_vat'}),
                                            (EntityCellRegularField, {'name': 'issuing_date'}),
                                            (EntityCellRegularField, {'name': 'expiration_date'}),
                                           ],
                               )

        create_hf(constants.DEFAULT_HFILTER_INVOICE,  _('Invoice view'),     Invoice)
        create_hf(constants.DEFAULT_HFILTER_QUOTE,    _('Quote view'),       Quote)
        create_hf(constants.DEFAULT_HFILTER_ORDER,    _('Sales order view'), SalesOrder)
        create_hf(constants.DEFAULT_HFILTER_CNOTE,    _('Credit note view'), CreditNote)
        create_hf(constants.DEFAULT_HFILTER_TEMPLATE, _('Template view'),    TemplateBase, status=False)

        def create_hf_lines(hf_pk, name, model):
            build_cell = EntityCellRegularField.build
            HeaderFilter.create(pk=hf_pk, name=name, model=model,
                                cells_desc=[build_cell(model=model, name='on_the_fly_item'),
                                            build_cell(model=model, name='quantity'),
                                            build_cell(model=model, name='unit_price'),
                                           ]
                               )

        create_hf_lines('billing-hg_product_lines', _('Product lines view'), ProductLine)
        create_hf_lines('billing-hg_service_lines', _('Service lines view'), ServiceLine)

        # ---------------------------
        for model in (Invoice, CreditNote, Quote, SalesOrder):
            SearchConfigItem.create_if_needed(model, ['name', 'number', 'status__name'])

        for model in (ProductLine, ServiceLine):
            SearchConfigItem.create_if_needed(model, [], disabled=True)

        # ---------------------------
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.payment_info_key.id,       defaults={'value': True})
        create_svalue(key_id=setting_keys.button_redirection_key.id, defaults={'value': True})

        # ---------------------------
        if not already_populated:
            create_if_needed(QuoteStatus, {'pk': 1}, name=pgettext('billing-quote', 'Pending'),  order=2)  # Default status
            create_if_needed(QuoteStatus, {'pk': 2}, name=pgettext('billing-quote', 'Accepted'), order=3, won=True)
            create_if_needed(QuoteStatus, {'pk': 3}, name=pgettext('billing-quote', 'Rejected'), order=4)
            create_if_needed(QuoteStatus, {'pk': 4}, name=pgettext('billing-quote', 'Created'),  order=1)

            # ---------------------------
            create_if_needed(SettlementTerms, {'pk': 1}, name=_('30 days'))
            create_if_needed(SettlementTerms, {'pk': 2}, name=_('Cash'))
            create_if_needed(SettlementTerms, {'pk': 3}, name=_('45 days'))
            create_if_needed(SettlementTerms, {'pk': 4}, name=_('60 days'))
            create_if_needed(SettlementTerms, {'pk': 5}, name=_('30 days, end month the 10'))

            # ---------------------------
            create_if_needed(AdditionalInformation, {'pk': 1}, name=_('Trainer accreditation'),
                             description=_('being certified trainer courses could be supported by your OPCA')
                            )

            # ---------------------------
            create_bmi = ButtonMenuItem.create_if_needed
            create_bmi(pk='billing-generate_invoice_number', model=Invoice, button=buttons.GenerateInvoiceNumberButton, order=0)

            create_bmi(pk='billing-convert_quote_to_invoice', model=Quote, button=buttons.ConvertToInvoiceButton, order=0)
            create_bmi(pk='billing-convert_quote_to_salesorder', model=Quote, button=buttons.ConvertToSalesOrderButton, order=1)

            create_bmi(pk='billing-convert_salesorder_to_invoice', model=SalesOrder, button=buttons.ConvertToInvoiceButton, order=0)

            create_bmi(pk='billing-quote_orga_button',      model=Organisation, button=buttons.AddQuoteButton,      order=100)
            create_bmi(pk='billing-salesorder_orga_button', model=Organisation, button=buttons.AddSalesOrderButton, order=101)
            create_bmi(pk='billing-invoice_orga_button',    model=Organisation, button=buttons.AddInvoiceButton,    order=102)

            create_bmi(pk='billing-quote_contact_button',      model=Contact, button=buttons.AddQuoteButton,      order=100)
            create_bmi(pk='billing-salesorder_contact_button', model=Contact, button=buttons.AddSalesOrderButton, order=101)
            create_bmi(pk='billing-invoice_contact_button',    model=Contact, button=buttons.AddInvoiceButton,    order=102)

            # ---------------------------
            create_cbci = CustomBrickConfigItem.objects.create
            build_cell = EntityCellRegularField.build

            def build_cells(model, *extra_cells):
                return [
                    build_cell(model, 'name'),
                    build_cell(model, 'number'),
                    build_cell(model, 'issuing_date'),
                    build_cell(model, 'expiration_date'),
                    build_cell(model, 'discount'),
                    build_cell(model, 'additional_info'),
                    build_cell(model, 'payment_terms'),
                    build_cell(model, 'currency'),
                    *extra_cells,
                    build_cell(model, 'comment'),
                    build_cell(model, 'description'),
                    # --
                    build_cell(model, 'created'),
                    build_cell(model, 'modified'),
                    build_cell(model, 'user'),
                ]

            cbci_invoice = create_cbci(id='billing-invoice_info',
                                       name=_('Invoice information'),
                                       content_type=Invoice,
                                       cells=build_cells(Invoice,
                                                         build_cell(Invoice, 'status'),
                                                         build_cell(Invoice, 'payment_type'),
                                                        ),
                                      )
            cbci_c_note   = create_cbci(id='billing-creditnote_info',
                                        name=_('Credit note information'),
                                        content_type=CreditNote,
                                        cells=build_cells(CreditNote, build_cell(CreditNote, 'status')),
                                       )
            cbci_quote   = create_cbci(id='billing-quote_info',
                                       name=_('Quote information'),
                                       content_type=Quote,
                                       cells=build_cells(Quote,
                                                         build_cell(Quote, 'status'),
                                                         build_cell(Quote, 'acceptation_date'),
                                                        ),
                                      )
            cbci_s_order = create_cbci(id='billing-salesorder_info',
                                       name=_('Salesorder information'),
                                       content_type=SalesOrder,
                                       cells=build_cells(SalesOrder, build_cell(SalesOrder, 'status')),
                                      )
            cbci_tbase   = create_cbci(id='billing-templatebase_info',
                                       name=pgettext('billing', 'Template information'),
                                       content_type=TemplateBase,
                                       cells=build_cells(TemplateBase,
                                                         EntityCellFunctionField.build(TemplateBase, 'get_verbose_status'),
                                                        ),
                                      )

            models_4_blocks = [(Invoice,      cbci_invoice, True),  # Boolean -> insert CreditNote block
                               (CreditNote,   cbci_c_note,  False),
                               (Quote,        cbci_quote,   True),
                               (SalesOrder,   cbci_s_order, True),
                               (TemplateBase, cbci_tbase,   False),
                              ]
            create_bdl = BrickDetailviewLocation.objects.create_if_needed
            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            for model, cbci, has_credit_notes in models_4_blocks:
                create_bdl(brick=bricks.ProductLinesBrick, order=10, zone=TOP, model=model)
                create_bdl(brick=bricks.ServiceLinesBrick, order=20, zone=TOP, model=model)

                if has_credit_notes:
                    create_bdl(brick=bricks.CreditNotesBrick, order=30, zone=TOP, model=model)

                create_bdl(brick=cbci.generate_id(),                    order=5,   zone=LEFT, model=model)
                create_bdl(brick=core_bricks.CustomFieldsBrick,         order=40,  zone=LEFT, model=model)
                create_bdl(brick=bricks.BillingPaymentInformationBrick, order=60,  zone=LEFT, model=model)
                create_bdl(brick=bricks.BillingPrettyAddressBrick,      order=70,  zone=LEFT, model=model)
                create_bdl(brick=core_bricks.PropertiesBrick,           order=450, zone=LEFT, model=model)
                create_bdl(brick=core_bricks.RelationsBrick,            order=500, zone=LEFT, model=model)

                create_bdl(brick=bricks.TargetBrick,       order=2,  zone=RIGHT, model=model)
                create_bdl(brick=bricks.TotalBrick,        order=3,  zone=RIGHT, model=model)
                create_bdl(brick=core_bricks.HistoryBrick, order=20, zone=RIGHT, model=model)

            if apps.is_installed('creme.assistants'):
                logger.info('Assistants app is installed => we use the assistants blocks on detail views')

                from creme.assistants.bricks import AlertsBrick, MemosBrick, TodosBrick, UserMessagesBrick

                for t in models_4_blocks:
                    model = t[0]
                    create_bdl(brick=TodosBrick,        order=100, zone=RIGHT, model=model)
                    create_bdl(brick=MemosBrick,        order=200, zone=RIGHT, model=model)
                    create_bdl(brick=AlertsBrick,       order=300, zone=RIGHT, model=model)
                    create_bdl(brick=UserMessagesBrick, order=400, zone=RIGHT, model=model)

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed => we use the documents block on detail views')

                from creme.documents.bricks import LinkedDocsBrick

                for t in models_4_blocks:
                    create_bdl(brick=LinkedDocsBrick, order=600, zone=RIGHT, model=t[0])

            create_bdl(brick=bricks.PaymentInformationBrick, order=300, zone=LEFT,  model=Organisation)
            create_bdl(brick=bricks.ReceivedInvoicesBrick,   order=14,  zone=RIGHT, model=Organisation)
            create_bdl(brick=bricks.ReceivedQuotesBrick,     order=18,  zone=RIGHT, model=Organisation)

            # ---------------------------
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
        invoices_report1 = create_report(name=_('All invoices of the current year'),
                                         filter=current_year_invoice_filter,
                                        )
        create_report_columns(invoices_report1)

        rgraph1 = create_graph(name=_('Sum of current year invoices total without taxes / month'),
                               # report=invoices_report1,
                               linked_report=invoices_report1,
                               abscissa='issuing_date', ordinate='total_no_vat__sum',
                               type=RGT_MONTH, is_count=False,
                              )
        create_graph(name=_('Sum of current year invoices total without taxes / invoices status'),
                     # report=invoices_report1,
                     linked_report=invoices_report1,
                     abscissa='status', ordinate='total_no_vat__sum',
                     type=RGT_FK, is_count=False,
                    )
        ibci = rgraph1.create_instance_brick_config_item()

        BrickHomeLocation.objects.create(brick_id=ibci.brick_id, order=11)

        # Create current year and unpaid invoices report -----------------------
        invoices_report2 = create_report(name=_('Invoices unpaid of the current year'),
                                         filter=current_year_unpaid_invoice_filter,
                                        )
        create_report_columns(invoices_report2)

        rgraph = create_graph(name=_('Sum of current year and unpaid invoices total without taxes / month'),
                              # report=invoices_report2,
                              linked_report=invoices_report2,
                              abscissa='issuing_date', ordinate='total_no_vat__sum',
                              type=RGT_MONTH, is_count=False,
                             )
        ibci = rgraph.create_instance_brick_config_item()

        BrickHomeLocation.objects.create(brick_id=ibci.brick_id, order=12)
