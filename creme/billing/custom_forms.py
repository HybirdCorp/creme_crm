from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme import billing
from creme.creme_core.gui.custom_form import (
    LAYOUT_DUAL_SECOND,
    CustomFormDefault,
    CustomFormDescriptor,
)

from .forms import base, templatebase

Invoice = billing.get_invoice_model()
Quote = billing.get_quote_model()
SalesOrder = billing.get_sales_order_model()
CreditNote = billing.get_credit_note_model()
TemplateBase = billing.get_template_base_model()


class _BaseCustomFormDefault(CustomFormDefault):
    main_fields = [
        'user',
        'name', 'number', 'status',
        'issuing_date', 'expiration_date',
        'discount', 'currency',
        'comment',
        'additional_info', 'payment_terms', 'payment_type',
    ]

    def groups_desc(self):
        descriptor = self.descriptor
        model = descriptor.model
        return [
            # LAYOUT_DUAL_FIRST
            self.group_desc_for_main_fields(),

            # LAYOUT_DUAL_SECOND
            {
                'name': gettext('Organisations'),
                'layout': LAYOUT_DUAL_SECOND,
                'cells': [
                    base.BillingSourceSubCell(model=model).into_cell(),
                    base.BillingTargetSubCell(model=model).into_cell(),
                ],
            },
            self.group_desc_for_description(),
            self.group_desc_for_customfields(),

            # LAYOUT_REGULAR
            *self.groups_desc_for_properties_n_relations(),
        ]


# ------------------------------------------------------------------------------
class InvoiceFormDefault(_BaseCustomFormDefault):
    main_fields = [
        *_BaseCustomFormDefault.main_fields,
        'buyers_order_number',
    ]


INVOICE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-invoice_creation',
    model=Invoice,
    verbose_name=_('Creation form for invoice'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=Invoice),
        base.BillingTargetSubCell(model=Invoice),
    ],
    default=InvoiceFormDefault,
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
    default=InvoiceFormDefault,
)


# ------------------------------------------------------------------------------
class QuoteFormDefault(_BaseCustomFormDefault):
    main_fields = [
        *_BaseCustomFormDefault.main_fields,
        'acceptation_date',
    ]


QUOTE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-quote_creation',
    model=Quote,
    verbose_name=_('Creation form for quote'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=Quote),
        base.BillingTargetSubCell(model=Quote),
    ],
    default=QuoteFormDefault,
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
    default=QuoteFormDefault,
)


# ------------------------------------------------------------------------------
class SalesOrderFormDefault(_BaseCustomFormDefault):
    pass


ORDER_CREATION_CFORM = CustomFormDescriptor(
    id='billing-sales_order_creation',
    model=SalesOrder,
    verbose_name=_('Creation form for salesorder'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=SalesOrder),
        base.BillingTargetSubCell(model=SalesOrder),
    ],
    default=SalesOrderFormDefault,
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
    default=SalesOrderFormDefault,
)


# ------------------------------------------------------------------------------
class CreditNoteFormDefault(_BaseCustomFormDefault):
    pass


CNOTE_CREATION_CFORM = CustomFormDescriptor(
    id='billing-credit_note_creation',
    model=CreditNote,
    verbose_name=_('Creation form for credit note'),
    base_form_class=base.BaseCustomForm,
    extra_sub_cells=[
        base.BillingSourceSubCell(model=CreditNote),
        base.BillingTargetSubCell(model=CreditNote),
    ],
    default=CreditNoteFormDefault,
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
    default=CreditNoteFormDefault,
)


# ------------------------------------------------------------------------------
class TemplateBaseFormDefault(_BaseCustomFormDefault):
    sub_cells = {
        # NB: not a problem that "status" is not a real field name ("status_uuid" is)
        #     see 'sub_cells' attribute documentation.
        'status': templatebase.BillingTemplateStatusSubCell,
    }


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
    default=TemplateBaseFormDefault,
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
    default=TemplateBaseFormDefault,
)

del Invoice
del Quote
del SalesOrder
del CreditNote
del TemplateBase
