# -*- coding: utf-8 -*-

from . import models


to_register = ((models.InvoiceStatus,         'invoice_status'),
               (models.QuoteStatus,           'quote_status'),
               (models.CreditNoteStatus,      'credit_note_status'),
               (models.SalesOrderStatus,      'sales_order_status'),
               (models.AdditionalInformation, 'additional_information'),
               (models.PaymentTerms,          'payment_terms'),
               (models.SettlementTerms,       'invoice_payment_type'),
              )
