# -*- coding: utf-8 -*-

from .models import (InvoiceStatus, QuoteStatus, SalesOrderStatus, CreditNoteStatus,
                     PaymentTerms, AdditionalInformation, SettlementTerms)


to_register = ((InvoiceStatus,         'invoice_status'),
               (QuoteStatus,           'quote_status'),
               (CreditNoteStatus,      'credit_note_status'),
               (SalesOrderStatus,      'sales_order_status'),
               (AdditionalInformation, 'additional_information'),
               (PaymentTerms,          'payment_terms'),
               (SettlementTerms,       'invoice_payment_type'),
              )
