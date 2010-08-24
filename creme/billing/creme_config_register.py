# -*- coding: utf-8 -*-

from models import InvoiceStatus, QuoteStatus, SalesOrderStatus, CreditNoteStatus


to_register = ((InvoiceStatus,    'invoice_status'),
               (QuoteStatus,      'quote_status'),
               (CreditNoteStatus,      'credit_note_status'),
               (SalesOrderStatus, 'sales_order_status'))
