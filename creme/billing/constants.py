# -*- coding: utf-8 -*-

from decimal import Decimal, ROUND_UP, ROUND_DOWN, ROUND_HALF_EVEN

DEFAULT_DECIMAL = Decimal()
DEFAULT_VAT = Decimal("19.6")
ROUND_POLICY = ROUND_UP
CURRENCY = "Euro"

REL_SUB_BILL_ISSUED = 'billing-subject_bill_issued'
REL_OBJ_BILL_ISSUED = 'billing-object_bill_issued'

REL_SUB_BILL_RECEIVED = 'billing-subject_bill_received'
REL_OBJ_BILL_RECEIVED = 'billing-object_bill_received'

DEFAULT_DRAFT_INVOICE_STATUS = 1
DEFAULT_INVOICE_STATUS = 2
