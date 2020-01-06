# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2018-2019  Hybird
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

from creme import billing

CreditNote   = billing.get_credit_note_model()
Quote        = billing.get_quote_model()
Invoice      = billing.get_invoice_model()
SalesOrder   = billing.get_sales_order_model()
TemplateBase = billing.get_template_base_model()

BILLING_MODELS = [
    CreditNote,
    Quote,
    Invoice,
    SalesOrder,
    TemplateBase,
]

# TODO : rework this !
CLASS_MAP = {
    'credit_note': CreditNote,  # NB: unused
    'invoice':     Invoice,
    'quote':       Quote,
    'sales_order': SalesOrder,
}

CONVERT_MATRIX = {
    Invoice:    {'quote'},
    Quote:      {'sales_order', 'invoice'},
    SalesOrder: {'invoice'},
}


def get_models_for_conversion(name):
    for model, conversions in CONVERT_MATRIX.items():
        if name in conversions:
            yield model
