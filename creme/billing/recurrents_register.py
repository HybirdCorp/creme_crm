# -*- coding: utf-8 -*-

from creme import billing

from .custom_forms import BTEMPLATE_CREATION_CFORM

TemplateBase = billing.get_template_base_model()
to_register = (
    (billing.get_invoice_model(),     TemplateBase, BTEMPLATE_CREATION_CFORM),
    (billing.get_quote_model(),       TemplateBase, BTEMPLATE_CREATION_CFORM),
    (billing.get_sales_order_model(), TemplateBase, BTEMPLATE_CREATION_CFORM),
    (billing.get_credit_note_model(), TemplateBase, BTEMPLATE_CREATION_CFORM),
)
