# -*- coding: utf-8 -*-

from creme import billing
from .forms.templatebase import TemplateBaseCreateForm


TemplateBase = billing.get_template_base_model()
to_register = ((billing.get_invoice_model(),     TemplateBase, TemplateBaseCreateForm),
               (billing.get_quote_model(),       TemplateBase, TemplateBaseCreateForm),
               (billing.get_sales_order_model(), TemplateBase, TemplateBaseCreateForm),
               (billing.get_credit_note_model(), TemplateBase, TemplateBaseCreateForm),
              )
