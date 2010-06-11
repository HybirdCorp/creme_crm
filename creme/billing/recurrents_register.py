# -*- coding: utf-8 -*-

from models import Invoice, Quote, SalesOrder, TemplateBase
from forms.templatebase import TemplateBaseCreateForm


to_register = ((Invoice,    TemplateBase, TemplateBaseCreateForm),
               (Quote,      TemplateBase, TemplateBaseCreateForm),
               (SalesOrder, TemplateBase, TemplateBaseCreateForm),
              )
