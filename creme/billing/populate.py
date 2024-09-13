################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

import creme.creme_core.bricks as core_bricks
from creme import billing, persons  # products
from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.gui.menu import ContainerEntry
from creme.creme_core.management.commands.creme_populate import BasePopulator
# from creme.creme_core.utils import create_if_needed
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

from . import bricks, buttons, constants, custom_forms, menu, setting_keys
from .core import BILLING_MODELS
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


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities']

    SEARCH = {
        'INVOICE':     ['name', 'number', 'status__name'],
        'QUOTE':       ['name', 'number', 'status__name'],
        'CREDIT_NOTE': ['name', 'number', 'status__name'],
        'SALES_ORDER': ['name', 'number', 'status__name'],
    }
    CREDIT_NOTE_STATUSES = [
        CreditNoteStatus(
            uuid='57191226-8ece-4a7d-bb5f-1b9635f41d9b',
            name=pgettext('billing-creditnote', 'Draft'), order=1,
            is_custom=False,
            is_default=True,
        ),
        # is_custom == True :
        CreditNoteStatus(
            uuid='42263776-44e0-4b63-b330-9a0237ab37c8',
            name=pgettext('billing-creditnote', 'Issued'), order=2,
        ),
        CreditNoteStatus(
            uuid='8fc73f0e-a427-4a07-b4f3-ae0b3eca9469',
            name=pgettext('billing-creditnote', 'Consumed'), order=3,
        ),
        CreditNoteStatus(
            uuid='0eee82dd-fb06-4de0-acf9-4d1d4b970399',
            name=pgettext('billing-creditnote', 'Out of date'), order=4,
        ),
    ]
    INVOICE_STATUSES = [
        InvoiceStatus(
            uuid='1bbb7c7e-610f-4366-b3de-b92d63c9cf23',
            name=pgettext('billing-invoice', 'Draft'), order=1,
            is_custom=False,
            is_default=True,
        ),
        InvoiceStatus(
            uuid='cc1209bb-e8a2-40bb-9361-4230d9e27bf2',
            name=pgettext('billing-invoice', 'To be sent'), order=2,
            is_custom=False,
            is_validated=True,
        ),
        # is_custom == True :
        InvoiceStatus(
            uuid='b8ed248b-5785-47ba-90d0-094ac9f813c7',
            name=pgettext('billing-invoice', 'Sent'), order=3,
            pending_payment=True,
        ),
        InvoiceStatus(
            uuid='017e8734-533d-4fc7-b355-c091748ccb34',
            name=pgettext('billing-invoice', 'Resulted'), order=5,
        ),
        InvoiceStatus(
            uuid='0d8da787-394c-4735-8cad-5eb3a2382415',
            name=pgettext('billing-invoice', 'Partly resulted'), order=4,
            pending_payment=True,
        ),
        InvoiceStatus(
            uuid='134ed1ba-efce-4984-baae-dae06fa27096',
            name=_('Collection'), order=7,
        ),
        InvoiceStatus(
            uuid='b5b256bd-6205-4f67-af3b-eb76b47e97fa',
            name=_('Resulted collection'), order=6,
        ),
        InvoiceStatus(
            uuid='b85ad6ce-9479-4c70-9241-97c03774e521',
            name=pgettext('billing-invoice', 'Canceled'), order=8,
        ),
    ]
    QUOTE_STATUSES = [
        # is_custom == True :
        QuoteStatus(
            uuid='9128fed1-e87d-477b-aa94-3d220f724f05',
            name=pgettext('billing-quote', 'Pending'), order=2,
            is_default=True,
        ),
        QuoteStatus(
            uuid='aa5b25ec-ea70-470f-91a6-402dffe933a8',
            name=pgettext('billing-quote', 'Accepted'), order=3,
            won=True, color='1dd420',
        ),
        QuoteStatus(
            uuid='7739a6ac-64a7-4f40-a04d-39a382b08d50',
            name=pgettext('billing-quote', 'Rejected'), order=4,
        ),
        QuoteStatus(
            uuid='9571e8bb-7a50-4453-a037-de829e189952',
            name=pgettext('billing-quote', 'Created'), order=1,
        ),
    ]
    SALES_ORDER_STATUSES = [
        SalesOrderStatus(
            uuid='bebdab5a-0281-4b34-a257-26602a19e320',
            name=pgettext('billing-salesorder', 'Issued'), order=1,
            is_default=True,
            is_custom=False,
        ),
        # is_custom == True :
        SalesOrderStatus(
            uuid='717ac4a7-97f8-4002-a555-544e4427191a',
            name=pgettext('billing-salesorder', 'Accepted'), order=3,
        ),
        SalesOrderStatus(
            uuid='a91aa135-b075-4a81-a06b-dd1839954a71',
            name=pgettext('billing-salesorder', 'Rejected'), order=4,
        ),
        SalesOrderStatus(
            uuid='ee4dd8f7-557f-46d8-8ed2-74c256875b84',
            name=pgettext('billing-salesorder', 'Created'),  order=2,
        ),
    ]
    PAYMENT_TERMS = [
        PaymentTerms(
            uuid='86b76130-4cac-4337-95ff-3e9021329956',
            name=_('Deposit'),
            description=_(r'20% deposit will be required'),
            is_custom=False,
        ),
    ]
    SETTLEMENT_TERMS = [
        # is_custom=True => only created during the first execution
        SettlementTerms(
            uuid='5d5db3d9-8af9-450a-9daa-67e78fae82f8', name=_('30 days'),
        ),
        SettlementTerms(
            uuid='36590d27-bf69-43fc-bdb1-d3b13d1fac8e', name=_('Cash'),
        ),
        SettlementTerms(
            uuid='2d0540fa-8be0-474c-ae97-70d721d17ee3', name=_('45 days'),
        ),
        SettlementTerms(
            uuid='3766296a-98ea-4341-a305-30e551d92550', name=_('60 days'),
        ),
        SettlementTerms(
            uuid='ad9152cb-bcb4-43ff-ba15-4b8d90557f23', name=_('30 days, end month the 10'),
        ),
    ]
    ADDITIONAL_INFORMATION = [
        # is_custom=True => only created during the first execution
        AdditionalInformation(
            uuid='1c3c5157-1a42-4b88-9b78-de15b41bdd96',
            name=_('Trainer accreditation'),
            description=_('being certified trainer courses could be supported by your OPCA'),
        ),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Contact      = persons.get_contact_model()
        self.Organisation = persons.get_organisation_model()

        self.CreditNote   = billing.get_credit_note_model()
        self.Invoice      = billing.get_invoice_model()
        self.Quote        = billing.get_quote_model()
        self.SalesOrder   = billing.get_sales_order_model()
        self.TemplateBase = billing.get_template_base_model()

        self.ProductLine = billing.get_product_line_model()
        self.ServiceLine = billing.get_service_line_model()

    def _already_populated(self):
        return RelationType.objects.filter(
            pk=constants.REL_SUB_BILL_ISSUED,
        ).exists()

    def _populate(self):
        super()._populate()
        self._populate_exporters_config()
        self._populate_payment_terms()
        self._populate_settlement_terms()
        self._populate_additional_information()

        self._populate_creditnote_statuses()
        self._populate_invoice_statuses()
        self._populate_quote_statuses()
        self._populate_order_statuses()

    def _first_populate(self):
        super()._first_populate()

        if apps.is_installed('creme.reports'):
            self._populate_reports()

    def _populate_exporters_config(self):
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

        for model in (
            self.CreditNote, self.Invoice, self.Quote, self.SalesOrder, self.TemplateBase,
        ):
            ExporterConfigItem.objects.get_or_create(
                content_type=get_ct(model),
                defaults={
                    'engine_id': engine_id,
                    'flavour_id': flavour_id,
                },
            )

    def _populate_payment_terms(self):
        # create_if_needed(
        #     PaymentTerms, {'pk': 1}, name=_('Deposit'),
        #     description=_(r'20% deposit will be required'),
        #     is_custom=False,
        # )
        self._save_minions(self.PAYMENT_TERMS)

    def _populate_settlement_terms(self):
        # create_if_needed(SettlementTerms, {'pk': 1}, name=_('30 days'))
        # create_if_needed(SettlementTerms, {'pk': 2}, name=_('Cash'))
        # create_if_needed(SettlementTerms, {'pk': 3}, name=_('45 days'))
        # create_if_needed(SettlementTerms, {'pk': 4}, name=_('60 days'))
        # create_if_needed(SettlementTerms, {'pk': 5}, name=_('30 days, end month the 10'))
        self._save_minions(self.SETTLEMENT_TERMS)

    def _populate_additional_information(self):
        # create_if_needed(
        #     AdditionalInformation,
        #     {'pk': 1}, name=_('Trainer accreditation'),
        #     description=_('being certified trainer courses could be supported by your OPCA'),
        # )
        self._save_minions(self.ADDITIONAL_INFORMATION)

    def _populate_creditnote_statuses(self):
        # def create_cnote_status(pk, name, **kwargs):
        #     create_if_needed(CreditNoteStatus, {'pk': pk}, name=name, **kwargs)
        #
        # create_cnote_status(
        #     1, pgettext('billing-creditnote', 'Draft'),
        #     order=1, is_custom=False, is_default=True,
        # )
        #
        # if not self.already_populated:
        #     create_cnote_status(2, pgettext('billing-creditnote', 'Issued'),      order=2)
        #     create_cnote_status(3, pgettext('billing-creditnote', 'Consumed'),    order=3)
        #     create_cnote_status(4, pgettext('billing-creditnote', 'Out of date'), order=4)
        self._save_minions(self.CREDIT_NOTE_STATUSES)

    def _populate_invoice_statuses(self):
        # def create_invoice_status(pk, name, **kwargs):
        #     create_if_needed(InvoiceStatus, {'pk': pk}, name=name, **kwargs)
        #
        # create_invoice_status(
        #     1, pgettext('billing-invoice', 'Draft'),
        #     order=1, is_custom=False, is_default=True,
        # )
        # create_invoice_status(
        #     2, pgettext('billing-invoice', 'To be sent'),
        #     order=2, is_custom=False, is_validated=True,
        # )
        #
        # if not self.already_populated:
        #     create_invoice_status(
        #         3, pgettext('billing-invoice', 'Sent'),
        #         order=3, pending_payment=True,
        #     )
        #     create_invoice_status(
        #         4, pgettext('billing-invoice', 'Resulted'),
        #         order=5,
        #     )
        #     create_invoice_status(
        #         5, pgettext('billing-invoice', 'Partly resulted'),
        #         order=4, pending_payment=True,
        #     )
        #     create_invoice_status(
        #         6, _('Collection'),
        #         order=7,
        #     )
        #     create_invoice_status(
        #         7, _('Resulted collection'),
        #         order=6,
        #     )
        #     create_invoice_status(
        #         8, pgettext('billing-invoice', 'Canceled'),
        #         order=8,
        #     )
        self._save_minions(self.INVOICE_STATUSES)

    def _populate_quote_statuses(self):
        # if not self.already_populated:
        #     def create_quote_status(pk, name, **kwargs):
        #         create_if_needed(QuoteStatus, {'pk': pk}, name=name, **kwargs)
        #
        #     # Default status
        #     create_quote_status(
        #         1, pgettext('billing-quote', 'Pending'),
        #         order=2, is_default=True,
        #     )
        #
        #     create_quote_status(
        #         2, pgettext('billing-quote', 'Accepted'),
        #         order=3, won=True, color='1dd420',
        #     )
        #     create_quote_status(
        #         3, pgettext('billing-quote', 'Rejected'),
        #         order=4,
        #     )
        #     create_quote_status(
        #         4, pgettext('billing-quote', 'Created'),
        #         order=1,
        #     )
        self._save_minions(self.QUOTE_STATUSES)

    def _populate_order_statuses(self):
        # def create_order_status(pk, name, **kwargs):
        #     create_if_needed(SalesOrderStatus, {'pk': pk}, name=name, **kwargs)
        #
        # # NB: pk=1 + is_custom=False --> default status
        # #     (used when a quote is converted in invoice for example)
        # create_order_status(
        #     1, pgettext('billing-salesorder', 'Issued'), order=1, is_custom=False)
        #
        # if not self.already_populated:
        #     create_order_status(2, pgettext('billing-salesorder', 'Accepted'), order=3)
        #     create_order_status(3, pgettext('billing-salesorder', 'Rejected'), order=4)
        #     create_order_status(4, pgettext('billing-salesorder', 'Created'),  order=2)
        self._save_minions(self.SALES_ORDER_STATUSES)

    def _populate_relation_types(self):
        # Product = products.get_product_model()
        # Service = products.get_service_model()
        line_models = [*lines_registry]

        create_rtype = RelationType.objects.smart_update_or_create
        create_rtype(
            (constants.REL_SUB_BILL_ISSUED, _('issued by'),  BILLING_MODELS),
            (constants.REL_OBJ_BILL_ISSUED, _('has issued'), [self.Organisation]),
            is_internal=True,
            minimal_display=(False, True),
        )
        create_rtype(
            (
                constants.REL_SUB_BILL_RECEIVED,
                _('received by'),
                BILLING_MODELS,
            ),
            (
                constants.REL_OBJ_BILL_RECEIVED,
                _('has received'),
                [self.Organisation, self.Contact],
            ),
            is_internal=True,
            minimal_display=(False, True),
        )
        create_rtype(
            (constants.REL_SUB_HAS_LINE, _('has the line'),   BILLING_MODELS),
            (constants.REL_OBJ_HAS_LINE, _('is the line of'), line_models),
            is_internal=True,
            minimal_display=(True, True),
        )
        create_rtype(
            (
                constants.REL_SUB_LINE_RELATED_ITEM,
                _('has the related item'),
                line_models,
            ),
            (
                constants.REL_OBJ_LINE_RELATED_ITEM,
                _('is the related item of'),
                # [Product, Service],
                {line_model.related_item_class() for line_model in line_models},
            ),
            is_internal=True,
        )
        create_rtype(
            (
                constants.REL_SUB_CREDIT_NOTE_APPLIED,
                _('is used in the billing document'),
                [self.CreditNote],
            ),
            (
                constants.REL_OBJ_CREDIT_NOTE_APPLIED,
                _('uses the credit note'),
                [self.Quote, self.SalesOrder, self.Invoice],
            ),
            is_internal=True,
            minimal_display=(True, True),
        )
        create_rtype(
            (
                constants.REL_SUB_INVOICE_FROM_QUOTE,
                _('(Invoice) converted from the Quote'),
                [self.Invoice],
            ),
            (
                constants.REL_OBJ_INVOICE_FROM_QUOTE,
                _('(Quote) converted to the Invoice'),
                [self.Quote],
            ),
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed '
                '=> an Invoice/Quote/SalesOrder can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(
                pk=REL_SUB_ACTIVITY_SUBJECT,
            ).add_subject_ctypes(self.Invoice, self.Quote, self.SalesOrder)

    def _populate_entity_filters(self):
        Invoice = self.Invoice

        self.unpaid_invoices = EntityFilter.objects.smart_update_or_create(
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
        self.unpaid_n_late_invoices_filter = EntityFilter.objects.smart_update_or_create(
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
        self.current_year_invoices_filter = EntityFilter.objects.smart_update_or_create(
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
        self.current_year_unpaid_invoices_filter = EntityFilter.objects.smart_update_or_create(
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

    def _create_header_filter(self, *, pk, name, model, status=True):
        HeaderFilter.objects.create_if_needed(
            pk=pk, name=name, model=model,
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                EntityCellRelation(
                    model=model,
                    rtype=RelationType.objects.get(id=constants.REL_SUB_BILL_RECEIVED),
                ),
                (EntityCellRegularField, {'name': 'number'}),
                (EntityCellRegularField, {'name': 'status'}) if status else None,
                (EntityCellRegularField, {'name': 'total_no_vat'}),
                (EntityCellRegularField, {'name': 'issuing_date'}),
                (EntityCellRegularField, {'name': 'expiration_date'}),
            ],
        )

    def _create_header_filter_for_line(self, *, pk, name, model):
        HeaderFilter.objects.create_if_needed(
            pk=pk, name=name, model=model,
            cells_desc=[
                (EntityCellRegularField, {'name': 'on_the_fly_item'}),
                (EntityCellRegularField, {'name': 'quantity'}),
                (EntityCellRegularField, {'name': 'unit_price'}),
            ],
        )

    def _populate_header_filters_for_invoice(self):
        self._create_header_filter(
            pk=constants.DEFAULT_HFILTER_INVOICE,
            name=_('Invoice view'),
            model=self.Invoice,
        )

    def _populate_header_filters_for_quote(self):
        self._create_header_filter(
            pk=constants.DEFAULT_HFILTER_QUOTE,
            name=_('Quote view'),
            model=self.Quote,
        )

    def _populate_header_filters_for_order(self):
        self._create_header_filter(
            pk=constants.DEFAULT_HFILTER_ORDER,
            name=_('Sales order view'),
            model=self.SalesOrder,
        )

    def _populate_header_filters_for_creditnode(self):
        self._create_header_filter(
            pk=constants.DEFAULT_HFILTER_CNOTE,
            name=_('Credit note view'),
            model=self.CreditNote,
        )

    def _populate_header_filters_for_templatebase(self):
        self._create_header_filter(
            pk=constants.DEFAULT_HFILTER_TEMPLATE,
            name=_('Template view'),
            model=self.TemplateBase,
            status=False,
        )

    def _populate_header_filters_for_productline(self):
        self._create_header_filter_for_line(
            pk='billing-hg_product_lines',
            name=_('Product lines view'),
            model=self.ProductLine,
        )

    def _populate_header_filters_for_serviceline(self):
        self._create_header_filter_for_line(
            pk='billing-hg_service_lines',
            name=_('Service lines view'),
            model=self.ServiceLine,
        )

    def _populate_header_filters(self):
        self._populate_header_filters_for_invoice()
        self._populate_header_filters_for_quote()
        self._populate_header_filters_for_order()
        self._populate_header_filters_for_creditnode()

        self._populate_header_filters_for_productline()
        self._populate_header_filters_for_serviceline()

    def _populate_custom_forms(self):
        create_cform = CustomFormConfigItem.objects.create_if_needed
        create_cform(descriptor=custom_forms.INVOICE_CREATION_CFORM)
        create_cform(descriptor=custom_forms.INVOICE_EDITION_CFORM)
        create_cform(descriptor=custom_forms.QUOTE_CREATION_CFORM)
        create_cform(descriptor=custom_forms.QUOTE_EDITION_CFORM)
        create_cform(descriptor=custom_forms.ORDER_CREATION_CFORM)
        create_cform(descriptor=custom_forms.ORDER_EDITION_CFORM)
        create_cform(descriptor=custom_forms.CNOTE_CREATION_CFORM)
        create_cform(descriptor=custom_forms.CNOTE_EDITION_CFORM)
        create_cform(descriptor=custom_forms.BTEMPLATE_CREATION_CFORM)
        create_cform(descriptor=custom_forms.BTEMPLATE_EDITION_CFORM)

    def _populate_search_config(self):
        create_sci = SearchConfigItem.objects.create_if_needed
        fields = self.SEARCH
        create_sci(model=self.Invoice,    fields=fields['INVOICE'])
        create_sci(model=self.CreditNote, fields=fields['CREDIT_NOTE'])
        create_sci(model=self.Quote,      fields=fields['QUOTE'])
        create_sci(model=self.SalesOrder, fields=fields['SALES_ORDER'])

        for model in (self.ProductLine, self.ServiceLine):
            create_sci(model=model, fields=[], disabled=True)

    def _populate_setting_values(self):
        create_svalue = SettingValue.objects.get_or_create
        create_svalue(key_id=setting_keys.payment_info_key.id,       defaults={'value': True})
        create_svalue(key_id=setting_keys.button_redirection_key.id, defaults={'value': True})

    def _populate_menu_config(self):
        menu_container = MenuConfigItem.objects.get_or_create(
            entry_id=ContainerEntry.id,
            entry_data={'label': _('Management')},
            defaults={'order': 50},
        )[0]

        create_mitem = partial(MenuConfigItem.objects.create, parent=menu_container)
        create_mitem(entry_id=menu.QuotesEntry.id,       order=10)
        create_mitem(entry_id=menu.InvoicesEntry.id,     order=15)
        create_mitem(entry_id=menu.CreditNotesEntry.id,  order=50)
        create_mitem(entry_id=menu.SalesOrdersEntry.id,  order=55)
        create_mitem(entry_id=menu.ProductLinesEntry.id, order=200)
        create_mitem(entry_id=menu.ServiceLinesEntry.id, order=210)

    def _populate_buttons_config_for_invoice(self):
        ButtonMenuItem.objects.create_if_needed(
            model=self.Invoice, button=buttons.GenerateInvoiceNumberButton, order=1001,
        )

    def _populate_buttons_config_for_quote(self):
        create_bmi = partial(ButtonMenuItem.objects.create_if_needed, model=self.Quote)
        create_bmi(button=buttons.ConvertToInvoiceButton,    order=1001)
        create_bmi(button=buttons.ConvertToSalesOrderButton, order=1002)

    def _populate_buttons_config_for_order(self):
        ButtonMenuItem.objects.create_if_needed(
            model=self.SalesOrder, button=buttons.ConvertToInvoiceButton, order=101,
        )

    def _populate_buttons_config_for_contact(self):
        create_bmi = partial(ButtonMenuItem.objects.create_if_needed, model=self.Contact)
        create_bmi(button=buttons.AddQuoteButton,      order=1010)
        create_bmi(button=buttons.AddSalesOrderButton, order=1011)
        create_bmi(button=buttons.AddInvoiceButton,    order=1012)

    def _populate_buttons_config_for_organisation(self):
        create_bmi = partial(ButtonMenuItem.objects.create_if_needed, model=self.Organisation)
        create_bmi(button=buttons.AddQuoteButton,      order=1010)
        create_bmi(button=buttons.AddSalesOrderButton, order=1011)
        create_bmi(button=buttons.AddInvoiceButton,    order=1012)

    def _populate_buttons_config(self):
        self._populate_buttons_config_for_invoice()
        self._populate_buttons_config_for_quote()
        self._populate_buttons_config_for_order()

        self._populate_buttons_config_for_contact()
        self._populate_buttons_config_for_organisation()

    def _populate_bricks_config_for_documents(self):
        # logger.info(
        #   'Documents app is installed
        #   => we use the documents block on detail views'
        # )

        from creme.documents.bricks import LinkedDocsBrick

        RIGHT = BrickDetailviewLocation.RIGHT

        for model in [
            self.Invoice, self.CreditNote, self.Quote, self.SalesOrder, self.TemplateBase,
        ]:
            BrickDetailviewLocation.objects.create_if_needed(
                brick=LinkedDocsBrick, order=600, zone=RIGHT, model=model,
            )

    def _populate_bricks_config_for_persons(self):
        LEFT = BrickDetailviewLocation.LEFT
        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': self.Organisation, 'zone': BrickDetailviewLocation.RIGHT},
            data=[
                {'brick': bricks.PaymentInformationBrick, 'order': 300, 'zone': LEFT},

                {'brick': bricks.ReceivedInvoicesBrick, 'order':  14},
                {'brick': bricks.ReceivedQuotesBrick,   'order':  18},
            ],
        )

    def _populate_bricks_config_for_assistants(self):
        logger.info(
            'Assistants app is installed => we use the assistants blocks on detail views'
        )

        import creme.assistants.bricks as a_bricks

        for model in [
            self.Invoice, self.CreditNote, self.Quote, self.SalesOrder, self.TemplateBase,
        ]:
            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': model, 'zone': BrickDetailviewLocation.RIGHT},
                data=[
                    {'brick': a_bricks.TodosBrick,        'order': 100},
                    {'brick': a_bricks.MemosBrick,        'order': 200},
                    {'brick': a_bricks.AlertsBrick,       'order': 300},
                    {'brick': a_bricks.UserMessagesBrick, 'order': 400},
                ],
            )

    def _create_custom_brick_item(self, *, model, uuid, name, extra_cells):
        build_cell = EntityCellRegularField.build

        return CustomBrickConfigItem.objects.create(
            uuid=uuid,
            name=name,
            content_type=model,
            # cells=build_cells(
            #     CreditNote,
            #     build_cell(CreditNote, 'status'),
            # ),
            cells=[
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
        )

    def _create_bricks_config(self, model, cbci: CustomBrickConfigItem, has_credit_notes=True):
        TOP   = BrickDetailviewLocation.TOP
        RIGHT = BrickDetailviewLocation.RIGHT

        data = [
            # LEFT
            {'brick': cbci.brick_id,                         'order':   5},
            {'brick': core_bricks.CustomFieldsBrick,         'order':  40},
            {'brick': bricks.BillingPaymentInformationBrick, 'order':  60},
            {'brick': bricks.BillingPrettyAddressBrick,      'order':  70},
            {'brick': core_bricks.PropertiesBrick,           'order': 450},
            {'brick': core_bricks.RelationsBrick,            'order': 500},

            {'brick': bricks.TargetBrick,       'order':  2, 'zone': RIGHT},
            {'brick': bricks.TotalBrick,        'order':  3, 'zone': RIGHT},
            {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},

            {'brick': bricks.ProductLinesBrick, 'order': 10, 'zone': TOP},
            {'brick': bricks.ServiceLinesBrick, 'order': 20, 'zone': TOP},
        ]
        if has_credit_notes:
            data.append({'brick': bricks.CreditNotesBrick, 'order': 30, 'zone': TOP})

        BrickDetailviewLocation.objects.multi_create(
            defaults={'model': model, 'zone': BrickDetailviewLocation.LEFT},
            data=data,
        )

    def _populate_bricks_config_for_invoice(self):
        Invoice = self.Invoice
        cbci = self._create_custom_brick_item(
            model=Invoice,
            # id='billing-invoice_info',
            uuid='d1ae20ac-98b5-4c4b-bf32-8c284c6eadae',
            name=_('Invoice information'),
            extra_cells=(
                EntityCellRegularField.build(Invoice, 'status'),
                # EntityCellRegularField.build(Invoice, 'payment_type'),
                EntityCellRegularField.build(Invoice, 'buyers_order_number'),
            ),
        )
        self._create_bricks_config(model=Invoice, cbci=cbci, has_credit_notes=True)

    def _populate_bricks_config_for_quote(self):
        Quote = self.Quote
        cbci = self._create_custom_brick_item(
            model=Quote,
            # id='billing-quote_info',
            uuid='eb3e5fcc-e929-4a15-b859-207a093bc4cb',
            name=_('Quote information'),
            extra_cells=(
                EntityCellRegularField.build(Quote, 'status'),
                EntityCellRegularField.build(Quote, 'acceptation_date'),
            ),
        )
        self._create_bricks_config(model=Quote, cbci=cbci, has_credit_notes=True)

    def _populate_bricks_config_for_order(self):
        SalesOrder = self.SalesOrder
        cbci = self._create_custom_brick_item(
            model=SalesOrder,
            # id='billing-salesorder_info',
            uuid='5e5b19c9-fa6e-43cf-a798-8b51b2ff73ce',
            name=_('Salesorder information'),
            extra_cells=(
                EntityCellRegularField.build(SalesOrder, 'status'),
            ),
        )
        self._create_bricks_config(model=SalesOrder, cbci=cbci, has_credit_notes=True)

    def _populate_bricks_config_for_creditnote(self):
        CreditNote = self.CreditNote
        cbci = self._create_custom_brick_item(
            model=CreditNote,
            # id='billing-creditnote_info',
            uuid='b3233bc2-cda8-4b07-ae4b-617b177120fc',
            name=_('Credit note information'),
            extra_cells=(
                EntityCellRegularField.build(CreditNote, 'status'),
            ),
        )
        self._create_bricks_config(model=CreditNote, cbci=cbci, has_credit_notes=False)

    def _populate_bricks_config_for_templatebase(self):
        TemplateBase = self.TemplateBase
        cbci = self._create_custom_brick_item(
            model=TemplateBase,
            # id='billing-templatebase_info',
            uuid='4653dc10-f2ce-455c-a0b2-30ff957e8f68',
            name=pgettext('billing', 'Template information'),
            extra_cells=(
                EntityCellFunctionField.build(TemplateBase, 'get_verbose_status'),
            ),
        )
        self._create_bricks_config(model=TemplateBase, cbci=cbci, has_credit_notes=False)

    def _populate_bricks_config(self):
        self._populate_bricks_config_for_invoice()
        self._populate_bricks_config_for_quote()
        self._populate_bricks_config_for_order()
        self._populate_bricks_config_for_creditnote()
        self._populate_bricks_config_for_templatebase()

        self._populate_bricks_config_for_persons()

        if apps.is_installed('creme.documents'):
            self._populate_bricks_config_for_documents()

        if apps.is_installed('creme.assistants'):
            self._populate_bricks_config_for_assistants()

    # def create_reports(self,
    #                    rt_sub_bill_received,
    #                    current_year_invoice_filter,
    #                    current_year_unpaid_invoice_filter,
    #                    ):
    def _populate_reports(self):
        logger.info(
            'Reports app is installed '
            '=> we create 2 billing reports, with 3 graphs, and related blocks in home'
        )

        # NB: the fixed UUIDs were added with Creme2.5 in order to facilitate
        #     import/export in 'creme_config'. So the Reports/ReportGraphes
        #     populated with previous versions will have different UUIDs.
        from functools import partial

        from django.contrib.auth import get_user_model

        from creme import reports
        from creme.reports.constants import RFT_FIELD, RFT_RELATION
        from creme.reports.core.graph.fetcher import SimpleGraphFetcher
        from creme.reports.models import Field

        admin = get_user_model().objects.get_admin()
        ReportGraph = reports.get_rgraph_model()

        Invoice = self.Invoice
        total_no_vat_cell = EntityCellRegularField.build(Invoice, 'total_no_vat')
        if total_no_vat_cell is None:
            logger.warning(
                'Invoice seems not having a field "total_no_vat" '
                '=> no Report/ReportGraph created.'
            )
            return

        # rt_sub_bill_received = RelationType.objects.get(id=constants.REL_SUB_BILL_RECEIVED)

        def create_report_columns(report):
            create_field = partial(Field.objects.create, report=report, type=RFT_FIELD)
            create_field(name='name',            order=1)
            # create_field(name=rt_sub_bill_received.id, order=2, type=RFT_RELATION)
            create_field(name=constants.REL_SUB_BILL_RECEIVED, order=2, type=RFT_RELATION)
            create_field(name='number',          order=3)
            create_field(name='status',          order=4)
            create_field(name='total_no_vat',    order=5)
            create_field(name='issuing_date',    order=6)
            create_field(name='expiration_date', order=7)

        create_report = partial(reports.get_report_model().objects.create, user=admin, ct=Invoice)
        create_graph = partial(ReportGraph.objects.create, user=admin)

        # Create current year invoices report ----------------------------------
        invoices_report1 = create_report(
            uuid='e8dc076c-16c5-462e-b32e-61c6e0249dfd',
            name=_('All invoices of the current year'),
            filter=self.current_year_invoices_filter,
        )
        create_report_columns(invoices_report1)

        cell_key = total_no_vat_cell.key
        rgraph1 = create_graph(
            uuid='c94e414d-931c-47bb-a7b9-144245997062',
            name=_('Sum of current year invoices total without taxes / month'),
            linked_report=invoices_report1,
            abscissa_cell_value='issuing_date', abscissa_type=ReportGraph.Group.MONTH,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=cell_key,
        )
        create_graph(
            uuid='94b3b88a-7350-4fae-9d9e-2d36a66677fb',
            name=_('Sum of current year invoices total without taxes / invoices status'),
            linked_report=invoices_report1,
            abscissa_cell_value='status', abscissa_type=ReportGraph.Group.FK,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=cell_key,
        )
        ibci1 = SimpleGraphFetcher(graph=rgraph1).create_brick_config_item(
            uuid='574e62e4-f5fb-4cb0-8e50-8bed100a83fd',
        )
        BrickHomeLocation.objects.create(brick_id=ibci1.brick_id, order=11)

        # Create current year and unpaid invoices report -----------------------
        invoices_report2 = create_report(
            uuid='2a1f7582-7e01-434a-b26f-6ee811e4c704',
            name=_('Invoices unpaid of the current year'),
            filter=self.current_year_unpaid_invoices_filter,
        )
        create_report_columns(invoices_report2)

        rgraph3 = create_graph(
            uuid='5388305f-0fcc-4ebb-b8a8-2cb4b3154c9c',
            name=_('Sum of current year and unpaid invoices total without taxes / month'),
            linked_report=invoices_report2,
            abscissa_cell_value='issuing_date', abscissa_type=ReportGraph.Group.MONTH,
            ordinate_type=ReportGraph.Aggregator.SUM,
            ordinate_cell_key=cell_key,
        )
        ibci3 = SimpleGraphFetcher(rgraph3).create_brick_config_item(
            uuid='9b9faf6f-0537-419f-842d-d9b3fc3cb321',
        )
        BrickHomeLocation.objects.create(brick_id=ibci3.brick_id, order=12)
