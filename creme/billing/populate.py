# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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
from functools import partial

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme import billing, persons, products
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.forms import LAYOUT_DUAL_FIRST, LAYOUT_DUAL_SECOND
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    ButtonMenuItem,
    CustomBrickConfigItem,
    CustomFormConfigItem,
    EntityFilter,
    HeaderFilter,
    MenuConfigItem,
    RelationType,
    SearchConfigItem,
    SettingValue,
)
from creme.creme_core.utils import create_if_needed

from . import bricks, buttons, constants, custom_forms, menu, setting_keys
from .core import BILLING_MODELS
from .forms.base import BillingSourceSubCell, BillingTargetSubCell
from .forms.templatebase import BillingTemplateStatusSubCell
from .models import (
    AdditionalInformation,
    CreditNoteStatus,
    ExporterConfigItem,
    InvoiceStatus,
    PaymentTerms,
    QuoteStatus,
    SalesOrderStatus,
    SettlementTerms,
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
        already_populated = RelationType.objects.filter(
            pk=constants.REL_SUB_BILL_ISSUED,
        ).exists()

        Contact      = persons.get_contact_model()
        Organisation = persons.get_organisation_model()
        Product = products.get_product_model()
        Service = products.get_service_model()

        # Relationships ---------------------------
        line_entities = [*lines_registry]
        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (constants.REL_SUB_BILL_ISSUED, _('issued by'),  BILLING_MODELS),
            (constants.REL_OBJ_BILL_ISSUED, _('has issued'), [Organisation]),
            is_internal=True,
            minimal_display=(False, True),
        )
        rt_sub_bill_received = create_rtype(
            (constants.REL_SUB_BILL_RECEIVED, _('received by'),  BILLING_MODELS),
            (constants.REL_OBJ_BILL_RECEIVED, _('has received'), [Organisation, Contact]),
            is_internal=True,
            minimal_display=(False, True),
        )[0]
        create_rtype(
            (constants.REL_SUB_HAS_LINE, _('has the line'),   BILLING_MODELS),
            (constants.REL_OBJ_HAS_LINE, _('is the line of'), line_entities),
            is_internal=True,
            minimal_display=(True, True),
        )
        create_rtype(
            (constants.REL_SUB_LINE_RELATED_ITEM, _('has the related item'),   line_entities),
            (constants.REL_OBJ_LINE_RELATED_ITEM, _('is the related item of'), [Product, Service]),
            is_internal=True,
        )
        create_rtype(
            (
                constants.REL_SUB_CREDIT_NOTE_APPLIED,
                _('is used in the billing document'),
                [CreditNote],
            ),
            (
                constants.REL_OBJ_CREDIT_NOTE_APPLIED,
                _('uses the credit note'),
                [Quote, SalesOrder, Invoice],
            ),
            is_internal=True,
            minimal_display=(True, True),
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed '
                '=> an Invoice/Quote/SalesOrder can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(
                pk=REL_SUB_ACTIVITY_SUBJECT,
            ).add_subject_ctypes(Invoice, Quote, SalesOrder)

        # Payment Terms ---------------------------
        create_if_needed(
            PaymentTerms, {'pk': 1}, name=_('Deposit'),
            description=_(r'20% deposit will be required'),
            is_custom=False,
        )

        # SalesOrder Status ---------------------------
        def create_order_status(pk, name, **kwargs):
            create_if_needed(SalesOrderStatus, {'pk': pk}, name=name, **kwargs)

        # NB: pk=1 + is_custom=False --> default status
        #     (used when a quote is converted in invoice for example)
        create_order_status(1, pgettext('billing-salesorder', 'Issued'), order=1, is_custom=False)

        if not already_populated:
            create_order_status(2, pgettext('billing-salesorder', 'Accepted'), order=3)
            create_order_status(3, pgettext('billing-salesorder', 'Rejected'), order=4)
            create_order_status(4, pgettext('billing-salesorder', 'Created'),  order=2)

        # Invoice Status ---------------------------
        def create_invoice_status(pk, name, **kwargs):
            create_if_needed(InvoiceStatus, {'pk': pk}, name=name, **kwargs)

        create_invoice_status(
            1, pgettext('billing-invoice', 'Draft'),      order=1, is_custom=False,
        )  # Default status
        create_invoice_status(
            2, pgettext('billing-invoice', 'To be sent'), order=2, is_custom=False,
        )

        if not already_populated:
            create_invoice_status(
                3, pgettext('billing-invoice', 'Sent'),            order=3, pending_payment=True,
            )
            create_invoice_status(
                4, pgettext('billing-invoice', 'Resulted'),        order=5,
            )
            create_invoice_status(
                5, pgettext('billing-invoice', 'Partly resulted'), order=4, pending_payment=True,
            )
            create_invoice_status(
                6, _('Collection'),                                order=7,
            )
            create_invoice_status(
                7, _('Resulted collection'),                       order=6,
            )
            create_invoice_status(
                8, pgettext('billing-invoice', 'Canceled'),        order=8,
            )

        # CreditNote Status ---------------------------
        def create_cnote_status(pk, name, **kwargs):
            create_if_needed(CreditNoteStatus, {'pk': pk}, name=name, **kwargs)

        create_cnote_status(1, pgettext('billing-creditnote', 'Draft'), order=1, is_custom=False)

        if not already_populated:
            create_cnote_status(2, pgettext('billing-creditnote', 'Issued'),      order=2)
            create_cnote_status(3, pgettext('billing-creditnote', 'Consumed'),    order=3)
            create_cnote_status(4, pgettext('billing-creditnote', 'Out of date'), order=4)

        # ---------------------------
        EntityFilter.objects.smart_update_or_create(
            'billing-invoices_unpaid', name=_('Invoices unpaid'),
            model=Invoice, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    operator=operators.EqualsOperator,
                    field_name='status__pending_payment',
                    values=[True],
                ),
            ],
        )
        EntityFilter.objects.smart_update_or_create(
            'billing-invoices_unpaid_late', name=_('Invoices unpaid and late'),
            model=Invoice, user='admin',
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    operator=operators.EqualsOperator,
                    field_name='status__pending_payment',
                    values=[True],
                ),
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    field_name='expiration_date',
                    date_range='in_past',
                ),
            ],
        )
        current_year_invoice_filter = EntityFilter.objects.smart_update_or_create(
            'billing-current_year_invoices', name=_('Current year invoices'),
            model=Invoice, user='admin',
            conditions=[
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    field_name='issuing_date',
                    date_range='current_year',
                ),
            ],
        )
        current_year_unpaid_invoice_filter = EntityFilter.objects.smart_update_or_create(
            'billing-current_year_unpaid_invoices',
            name=_('Current year and unpaid invoices'),
            model=Invoice, user='admin',
            conditions=[
                condition_handler.DateRegularFieldConditionHandler.build_condition(
                    model=Invoice,
                    field_name='issuing_date',
                    date_range='current_year',
                ),
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
            HeaderFilter.objects.create_if_needed(
                pk=hf_pk, name=name, model=model,
                cells_desc=[
                    (EntityCellRegularField, {'name': 'name'}),
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
        create_hf(
            constants.DEFAULT_HFILTER_TEMPLATE, _('Template view'),    TemplateBase, status=False,
        )

        def create_hf_lines(hf_pk, name, model):
            build_cell = EntityCellRegularField.build
            HeaderFilter.objects.create_if_needed(
                pk=hf_pk, name=name, model=model,
                cells_desc=[
                    build_cell(model=model, name='on_the_fly_item'),
                    build_cell(model=model, name='quantity'),
                    build_cell(model=model, name='unit_price'),
                ],
            )

        create_hf_lines('billing-hg_product_lines', _('Product lines view'), ProductLine)
        create_hf_lines('billing-hg_service_lines', _('Service lines view'), ServiceLine)

        # ---------------------------
        creation_only_groups_desc = [
            {
                'name': _('Properties'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.CREME_PROPERTIES},
                    ),
                ],
            }, {
                'name': _('Relationships'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.RELATIONS},
                    ),
                ],
            },
        ]

        def build_custom_form_items(model, creation_descriptor, edition_descriptor, field_names):
            base_groups = [
                {
                    'name': _('General information'),
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        *(
                            (EntityCellRegularField, {'name': fname})
                            for fname in field_names
                        ),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                }, {
                    'name': _('Organisations'),
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        BillingSourceSubCell(model=model).into_cell(),
                        BillingTargetSubCell(model=model).into_cell(),
                    ],
                }, {
                    'name': _('Description'),
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        (EntityCellRegularField, {'name': 'description'}),
                    ],
                }, {
                    'name': _('Custom fields'),
                    'layout': LAYOUT_DUAL_SECOND,
                    'cells': [
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                        ),
                    ],
                },
            ]

            CustomFormConfigItem.objects.create_if_needed(
                descriptor=creation_descriptor,
                groups_desc=[
                    *base_groups,
                    *creation_only_groups_desc,
                ],
            )
            CustomFormConfigItem.objects.create_if_needed(
                descriptor=edition_descriptor,
                groups_desc=base_groups,
            )

        common_field_names = [
            'user',
            'name',
            'number',
            'status',
            'issuing_date',
            'expiration_date',
            'discount',
            'currency',
            'comment',
            'additional_info',
            'payment_terms',
            'payment_type',
        ]
        build_custom_form_items(
            model=Invoice,
            creation_descriptor=custom_forms.INVOICE_CREATION_CFORM,
            edition_descriptor=custom_forms.INVOICE_EDITION_CFORM,
            # field_names=[
            #     'user',
            #     'name',
            #     'number',
            #     'status',
            #     'issuing_date',
            #     'expiration_date',
            #     'discount',
            #     'currency',
            #     'comment',
            #     'additional_info',
            #     'payment_terms',
            #     'payment_type',
            #     'buyers_order_number',
            # ],
            field_names=[*common_field_names, 'buyers_order_number'],
        )
        build_custom_form_items(
            model=Quote,
            creation_descriptor=custom_forms.QUOTE_CREATION_CFORM,
            edition_descriptor=custom_forms.QUOTE_EDITION_CFORM,
            # field_names=[
            #     'user',
            #     'name',
            #     'number',
            #     'status',
            #     'issuing_date',
            #     'expiration_date',
            #     'discount',
            #     'currency',
            #     'comment',
            #     'additional_info',
            #     'payment_terms',
            #     'acceptation_date',
            # ],
            field_names=[*common_field_names, 'acceptation_date'],
        )
        build_custom_form_items(
            model=SalesOrder,
            creation_descriptor=custom_forms.ORDER_CREATION_CFORM,
            edition_descriptor=custom_forms.ORDER_EDITION_CFORM,
            # field_names=[
            #     'user',
            #     'name',
            #     'number',
            #     'status',
            #     'issuing_date',
            #     'expiration_date',
            #     'discount',
            #     'currency',
            #     'comment',
            #     'additional_info',
            #     'payment_terms',
            # ],
            field_names=common_field_names,
        )
        build_custom_form_items(
            model=CreditNote,
            creation_descriptor=custom_forms.CNOTE_CREATION_CFORM,
            edition_descriptor=custom_forms.CNOTE_EDITION_CFORM,
            # field_names=[
            #     'user',
            #     'name',
            #     'number',
            #     'status',
            #     'issuing_date',
            #     'expiration_date',
            #     'discount',
            #     'currency',
            #     'comment',
            #     'additional_info',
            #     'payment_terms',
            # ],
            field_names=common_field_names,
        )

        common_template_groups_desc = [
            {
                'name': _('General information'),
                'cells': [
                    (EntityCellRegularField, {'name': 'user'}),
                    (EntityCellRegularField, {'name': 'name'}),
                    (EntityCellRegularField, {'name': 'number'}),
                    BillingTemplateStatusSubCell(model=TemplateBase).into_cell(),
                    (EntityCellRegularField, {'name': 'issuing_date'}),
                    (EntityCellRegularField, {'name': 'expiration_date'}),
                    (EntityCellRegularField, {'name': 'discount'}),
                    (EntityCellRegularField, {'name': 'currency'}),
                    (EntityCellRegularField, {'name': 'comment'}),
                    (EntityCellRegularField, {'name': 'additional_info'}),
                    (EntityCellRegularField, {'name': 'payment_terms'}),
                    (EntityCellRegularField, {'name': 'payment_type'}),
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                    ),
                ],
            }, {
                'name': _('Organisations'),
                'cells': [
                    BillingSourceSubCell(model=TemplateBase).into_cell(),
                    BillingTargetSubCell(model=TemplateBase).into_cell(),
                ],
            }, {
                'name': _('Description'),
                'cells': [
                    (EntityCellRegularField, {'name': 'description'}),
                ],
            }, {
                'name': _('Custom fields'),
                'cells': [
                    (
                        EntityCellCustomFormSpecial,
                        {'name': EntityCellCustomFormSpecial.REMAINING_CUSTOMFIELDS},
                    ),
                ],
            },
        ]
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.BTEMPLATE_CREATION_CFORM,
            groups_desc=[
                *common_template_groups_desc,
                *creation_only_groups_desc,
            ],
        )
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=custom_forms.BTEMPLATE_EDITION_CFORM,
            groups_desc=common_template_groups_desc,
        )

        # ---------------------------
        get_ct = ContentType.objects.get_for_model
        engine_id = ''
        flavour_id = ''

        if 'creme.billing.exporters.xhtml2pdf.Xhtml2pdfExportEngine' in settings.BILLING_EXPORTERS:
            from creme.billing.exporters.xhtml2pdf import Xhtml2pdfExportEngine
            from creme.creme_core.utils import l10n

            # TODO: add the country in settings & use it...
            country = l10n.FR
            language = 'fr_FR'
            theme = 'cappuccino'
            try:
                Xhtml2pdfExportEngine.FLAVOURS_INFO[country][language][theme]
            except KeyError:
                pass
            else:
                engine_id = Xhtml2pdfExportEngine.id
                flavour_id = f'{country}/{language}/{theme}'

        for model in (CreditNote, Invoice, Quote, SalesOrder, TemplateBase):
            ExporterConfigItem.objects.get_or_create(
                content_type=get_ct(model),
                defaults={
                    'engine_id': engine_id,
                    'flavour_id': flavour_id,
                },
            )

        # ---------------------------
        for model in (Invoice, CreditNote, Quote, SalesOrder):
            SearchConfigItem.objects.create_if_needed(model, ['name', 'number', 'status__name'])

        for model in (ProductLine, ServiceLine):
            SearchConfigItem.objects.create_if_needed(model, [], disabled=True)

        # ---------------------------
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.payment_info_key.id,       defaults={'value': True})
        create_svalue(key_id=setting_keys.button_redirection_key.id, defaults={'value': True})

        # ---------------------------
        # TODO: move to "not already_populated" section in creme2.4
        if not MenuConfigItem.objects.filter(entry_id__startswith='billing-').exists():
            container = MenuConfigItem.objects.get_or_create(
                entry_id=ContainerEntry.id,
                entry_data={'label': _('Management')},
                defaults={'order': 50},
            )[0]

            create_mitem = partial(MenuConfigItem.objects.create, parent=container)
            create_mitem(entry_id=menu.QuotesEntry.id,       order=10)
            create_mitem(entry_id=menu.InvoicesEntry.id,     order=15)
            create_mitem(entry_id=menu.CreditNotesEntry.id,  order=50)
            create_mitem(entry_id=menu.SalesOrdersEntry.id,  order=55)
            create_mitem(entry_id=menu.ProductLinesEntry.id, order=200)
            create_mitem(entry_id=menu.ServiceLinesEntry.id, order=210)

        # ---------------------------
        if not already_populated:
            def create_quote_status(pk, name, **kwargs):
                create_if_needed(QuoteStatus, {'pk': pk}, name=name, **kwargs)

            # Default status
            create_quote_status(1, pgettext('billing-quote', 'Pending'),  order=2)

            create_quote_status(2, pgettext('billing-quote', 'Accepted'), order=3, won=True)
            create_quote_status(3, pgettext('billing-quote', 'Rejected'), order=4)
            create_quote_status(4, pgettext('billing-quote', 'Created'),  order=1)

            # ---------------------------
            create_if_needed(SettlementTerms, {'pk': 1}, name=_('30 days'))
            create_if_needed(SettlementTerms, {'pk': 2}, name=_('Cash'))
            create_if_needed(SettlementTerms, {'pk': 3}, name=_('45 days'))
            create_if_needed(SettlementTerms, {'pk': 4}, name=_('60 days'))
            create_if_needed(SettlementTerms, {'pk': 5}, name=_('30 days, end month the 10'))

            # ---------------------------
            create_if_needed(
                AdditionalInformation,
                {'pk': 1}, name=_('Trainer accreditation'),
                description=_('being certified trainer courses could be supported by your OPCA')
            )

            # ---------------------------
            create_bmi = ButtonMenuItem.objects.create_if_needed
            create_bmi(model=Invoice, button=buttons.GenerateInvoiceNumberButton, order=0)

            create_bmi(model=Quote, button=buttons.ConvertToInvoiceButton,    order=0)
            create_bmi(model=Quote, button=buttons.ConvertToSalesOrderButton, order=1)

            create_bmi(model=SalesOrder, button=buttons.ConvertToInvoiceButton, order=0)

            create_bmi(model=Organisation, button=buttons.AddQuoteButton,      order=100)
            create_bmi(model=Organisation, button=buttons.AddSalesOrderButton, order=101)
            create_bmi(model=Organisation, button=buttons.AddInvoiceButton,    order=102)

            create_bmi(model=Contact, button=buttons.AddQuoteButton,      order=100)
            create_bmi(model=Contact, button=buttons.AddSalesOrderButton, order=101)
            create_bmi(model=Contact, button=buttons.AddInvoiceButton,    order=102)

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
                    build_cell(model, 'payment_type'),
                    build_cell(model, 'currency'),
                    *extra_cells,
                    build_cell(model, 'comment'),
                    build_cell(model, 'description'),
                    # --
                    build_cell(model, 'created'),
                    build_cell(model, 'modified'),
                    build_cell(model, 'user'),
                ]

            cbci_invoice = create_cbci(
                id='billing-invoice_info',
                name=_('Invoice information'),
                content_type=Invoice,
                cells=build_cells(
                    Invoice,
                    build_cell(Invoice, 'status'),
                    # build_cell(Invoice, 'payment_type'),
                    build_cell(Invoice, 'buyers_order_number'),
                ),
            )
            cbci_c_note = create_cbci(
                id='billing-creditnote_info',
                name=_('Credit note information'),
                content_type=CreditNote,
                cells=build_cells(
                    CreditNote,
                    build_cell(CreditNote, 'status'),
                ),
            )
            cbci_quote = create_cbci(
                id='billing-quote_info',
                name=_('Quote information'),
                content_type=Quote,
                cells=build_cells(
                    Quote,
                    build_cell(Quote, 'status'),
                    build_cell(Quote, 'acceptation_date'),
                ),
            )
            cbci_s_order = create_cbci(
                id='billing-salesorder_info',
                name=_('Salesorder information'),
                content_type=SalesOrder,
                cells=build_cells(
                    SalesOrder,
                    build_cell(SalesOrder, 'status'),
                ),
            )
            cbci_tbase = create_cbci(
                id='billing-templatebase_info',
                name=pgettext('billing', 'Template information'),
                content_type=TemplateBase,
                cells=build_cells(
                    TemplateBase,
                    EntityCellFunctionField.build(TemplateBase, 'get_verbose_status'),
                ),
            )

            models_4_blocks = [
                (Invoice,      cbci_invoice, True),  # Boolean -> insert CreditNote block
                (CreditNote,   cbci_c_note,  False),
                (Quote,        cbci_quote,   True),
                (SalesOrder,   cbci_s_order, True),
                (TemplateBase, cbci_tbase,   False),
            ]

            TOP   = BrickDetailviewLocation.TOP
            LEFT  = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            for model, cbci, has_credit_notes in models_4_blocks:
                data = [
                    # LEFT
                    {'brick': cbci.brick_id,                         'order':   5},
                    {'brick': core_bricks.CustomFieldsBrick,         'order':  40},
                    {'brick': bricks.BillingPaymentInformationBrick, 'order':  60},
                    {'brick': bricks.BillingPrettyAddressBrick,      'order':  70},
                    {'brick': core_bricks.PropertiesBrick,           'order': 450},
                    {'brick': core_bricks.RelationsBrick,            'order': 500},

                    {'brick': bricks.TargetBrick,       'order':  2,  'zone': RIGHT},
                    {'brick': bricks.TotalBrick,        'order':  3,  'zone': RIGHT},
                    {'brick': core_bricks.HistoryBrick, 'order': 20,  'zone': RIGHT},

                    {'brick': bricks.ProductLinesBrick, 'order': 10,  'zone': TOP},
                    {'brick': bricks.ServiceLinesBrick, 'order': 20,  'zone': TOP},
                ]
                if has_credit_notes:
                    data.append({'brick': bricks.CreditNotesBrick, 'order': 30, 'zone': TOP})

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': model, 'zone': LEFT}, data=data,
                )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed => we use the assistants blocks on detail views'
                )

                from creme.assistants import bricks as a_bricks

                for t in models_4_blocks:
                    BrickDetailviewLocation.objects.multi_create(
                        defaults={'model': t[0], 'zone': RIGHT},
                        data=[
                            {'brick': a_bricks.TodosBrick,        'order': 100},
                            {'brick': a_bricks.MemosBrick,        'order': 200},
                            {'brick': a_bricks.AlertsBrick,       'order': 300},
                            {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                        ],
                    )

            if apps.is_installed('creme.documents'):
                # logger.info(
                #   'Documents app is installed
                #   => we use the documents block on detail views'
                # )

                from creme.documents.bricks import LinkedDocsBrick

                for t in models_4_blocks:
                    BrickDetailviewLocation.objects.create_if_needed(
                        brick=LinkedDocsBrick, order=600, zone=RIGHT, model=t[0],
                    )

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Organisation, 'zone': RIGHT},
                data=[
                    {'brick': bricks.PaymentInformationBrick, 'order': 300, 'zone': LEFT},

                    {'brick': bricks.ReceivedInvoicesBrick,  'order':  14},
                    {'brick': bricks.ReceivedQuotesBrick,    'order':  18},
                ],
            )

            # ---------------------------
            if apps.is_installed('creme.reports'):
                logger.info(
                    'Reports app is installed '
                    '=> we create 2 billing reports, with 3 graphs, and related blocks in home'
                )
                self.create_reports(
                    rt_sub_bill_received,
                    current_year_invoice_filter,
                    current_year_unpaid_invoice_filter,
                )

    def create_reports(
            self,
            rt_sub_bill_received, current_year_invoice_filter,
            current_year_unpaid_invoice_filter):
        from functools import partial

        from django.contrib.auth import get_user_model

        from creme import reports
        # from creme.reports.constants import (
        #     RFT_FIELD,
        #     RFT_RELATION,
        #     RGA_SUM,
        #     RGT_FK,
        #     RGT_MONTH,
        # )
        from creme.reports.constants import RFT_FIELD, RFT_RELATION
        from creme.reports.core.graph.fetcher import SimpleGraphFetcher
        from creme.reports.models import Field

        admin = get_user_model().objects.get_admin()
        ReportGraph = reports.get_rgraph_model()

        total_no_vat_cell = EntityCellRegularField.build(Invoice, 'total_no_vat')
        if total_no_vat_cell is None:
            logger.warning(
                'Invoice seems not having a field "total_no_vat" '
                '=> no Report/ReportGraph created.'
            )
            return

        def create_report_columns(report):
            create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
            create_field(name='name',                  order=1)
            create_field(name=rt_sub_bill_received.id, order=2, type=RFT_RELATION)
            create_field(name='number',                order=3)
            create_field(name='status',                order=4)
            create_field(name='total_no_vat',          order=5)
            create_field(name='issuing_date',          order=6)
            create_field(name='expiration_date',       order=7)

        create_report = partial(reports.get_report_model().objects.create, user=admin, ct=Invoice)
        create_graph = partial(ReportGraph.objects.create, user=admin)

        # Create current year invoices report ----------------------------------
        invoices_report1 = create_report(
            name=_('All invoices of the current year'),
            filter=current_year_invoice_filter,
        )
        create_report_columns(invoices_report1)

        cell_key = total_no_vat_cell.key
        rgraph1 = create_graph(
            name=_('Sum of current year invoices total without taxes / month'),
            linked_report=invoices_report1,
            # abscissa_cell_value='issuing_date', abscissa_type=RGT_MONTH,
            abscissa_cell_value='issuing_date', abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=cell_key,
        )
        create_graph(
            name=_('Sum of current year invoices total without taxes / invoices status'),
            linked_report=invoices_report1,
            # abscissa_cell_value='status', abscissa_type=RGT_FK,
            abscissa_cell_value='status', abscissa_type=ReportGraph.Group.FK,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=cell_key,
        )
        ibci1 = SimpleGraphFetcher(graph=rgraph1).create_brick_config_item()
        BrickHomeLocation.objects.create(brick_id=ibci1.brick_id, order=11)

        # Create current year and unpaid invoices report -----------------------
        invoices_report2 = create_report(
            name=_('Invoices unpaid of the current year'),
            filter=current_year_unpaid_invoice_filter,
        )
        create_report_columns(invoices_report2)

        rgraph3 = create_graph(
            name=_('Sum of current year and unpaid invoices total without taxes / month'),
            linked_report=invoices_report2,
            # abscissa_cell_value='issuing_date', abscissa_type=RGT_MONTH,
            abscissa_cell_value='issuing_date', abscissa_type=ReportGraph.Group.MONTH,
            # ordinate_type=RGA_SUM,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=cell_key,
        )
        ibci3 = SimpleGraphFetcher(rgraph3).create_brick_config_item()
        BrickHomeLocation.objects.create(brick_id=ibci3.brick_id, order=12)
