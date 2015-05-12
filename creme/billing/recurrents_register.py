# -*- coding: utf-8 -*-

from . import (get_credit_note_model, get_invoice_model, get_quote_model,
        get_sales_order_model, get_template_base_model)
#from .models import Invoice, Quote, SalesOrder, TemplateBase, CreditNote
from .forms.templatebase import TemplateBaseCreateForm


#to_register = ((Invoice,    TemplateBase, TemplateBaseCreateForm),
#               (Quote,      TemplateBase, TemplateBaseCreateForm),
#               (SalesOrder, TemplateBase, TemplateBaseCreateForm),
#               (CreditNote, TemplateBase, TemplateBaseCreateForm),
#              )
TemplateBase = get_template_base_model()
to_register = ((get_invoice_model(),     TemplateBase, TemplateBaseCreateForm),
               (get_quote_model(),       TemplateBase, TemplateBaseCreateForm),
               (get_sales_order_model(), TemplateBase, TemplateBaseCreateForm),
               (get_credit_note_model(), TemplateBase, TemplateBaseCreateForm),
              )
