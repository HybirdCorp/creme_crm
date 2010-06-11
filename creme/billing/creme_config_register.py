# -*- coding: utf-8 -*-

from models import InvoiceStatus, QuoteStatus, SalesOrderStatus


to_register = ((InvoiceStatus,    'invoice_status'),
               (QuoteStatus,      'quote_status'),
               (SalesOrderStatus, 'sales_order_status'))
