# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import billing
from creme.creme_core.gui.custom_form import CustomFormDescriptor

from .forms import base, templatebase

Invoice = billing.get_invoice_model()
Quote = billing.get_quote_model()
SalesOrder = billing.get_sales_order_model()
CreditNote = billing.get_credit_note_model()
TemplateBase = billing.get_template_base_model()

INVOICE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-invoice_creation',
    model=Invoice,
    verbose_name=_('Creation form for invoice'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=Invoice),
        base.BillingTargetSubCell(model=Invoice),
    ],
)
INVOICE_EDITION_CFORM = CustomFormDescriptor(
    id='billing-invoice_edition',
    model=Invoice,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for invoice'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=Invoice),
        base.BillingTargetSubCell(model=Invoice),
    ],
)

QUOTE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-quote_creation',
    model=Quote,
    verbose_name=_('Creation form for quote'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=Quote),
        base.BillingTargetSubCell(model=Quote),
    ],
)
QUOTE_EDITION_CFORM = CustomFormDescriptor(
    id='billing-quote_edition',
    model=Quote,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for quote'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=Quote),
        base.BillingTargetSubCell(model=Quote),
    ],
)

ORDER_CREATION_CFORM = CustomFormDescriptor(
    id='billing-sales_order_creation',
    model=SalesOrder,
    verbose_name=_('Creation form for salesorder'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=SalesOrder),
        base.BillingTargetSubCell(model=SalesOrder),
    ],
)
ORDER_EDITION_CFORM = CustomFormDescriptor(
    id='billing-sales_order_edition',
    model=SalesOrder,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for salesorder'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=SalesOrder),
        base.BillingTargetSubCell(model=SalesOrder),
    ],
)

CNOTE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-credit_note_creation',
    model=CreditNote,
    verbose_name=_('Creation form for credit note'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=CreditNote),
        base.BillingTargetSubCell(model=CreditNote),
    ],
)
CNOTE_EDITION_CFORM = CustomFormDescriptor(
    id='billing-credit_note_edition',
    model=CreditNote,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=_('Edition form for credit note'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=CreditNote),
        base.BillingTargetSubCell(model=CreditNote),
    ],
)

BTEMPLATE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-template_creation',
    model=TemplateBase,
    verbose_name=pgettext_lazy('billing', 'Creation form for template'),
    base_form_class=templatebase.BaseTemplateCreationCustomForm,
    extra_sub_cells=[
        templatebase.BillingTemplateStatusSubCell(model=TemplateBase),
        base.BillingSourceSubCell(model=TemplateBase),
        base.BillingTargetSubCell(model=TemplateBase),
    ],
)
BTEMPLATE_EDITION_CFORM = CustomFormDescriptor(
    id='billing-template_edition',
    model=TemplateBase,
    form_type=CustomFormDescriptor.EDITION_FORM,
    verbose_name=pgettext_lazy('billing', 'Edition form for template'),
    base_form_class=templatebase.BaseTemplateCreationCustomForm,
    extra_sub_cells=[
        templatebase.BillingTemplateStatusSubCell(model=TemplateBase),
        base.BillingSourceSubCell(model=TemplateBase),
        base.BillingTargetSubCell(model=TemplateBase),
    ],
)

del Invoice
del Quote
del SalesOrder
del CreditNote
del TemplateBase
