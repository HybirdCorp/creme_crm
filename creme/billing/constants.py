# NB: other possibilities: ROUND_UP ROUND_DOWN ROUND_HALF_EVEN
from decimal import ROUND_HALF_UP, Decimal

DEFAULT_DECIMAL = Decimal()

ROUND_POLICY = ROUND_HALF_UP

REL_SUB_BILL_ISSUED = 'billing-subject_bill_issued'
REL_OBJ_BILL_ISSUED = 'billing-object_bill_issued'

REL_SUB_BILL_RECEIVED = 'billing-subject_bill_received'
REL_OBJ_BILL_RECEIVED = 'billing-object_bill_received'

REL_SUB_HAS_LINE = 'billing-subject_had_line'
REL_OBJ_HAS_LINE = 'billing-object_had_line'

REL_SUB_LINE_RELATED_ITEM = 'billing-subject_line_related_item'
REL_OBJ_LINE_RELATED_ITEM = 'billing-object_line_related_item'

REL_SUB_CREDIT_NOTE_APPLIED = 'billing-subject_credit_note_applied'
REL_OBJ_CREDIT_NOTE_APPLIED = 'billing-object_credit_note_applied'

REL_SUB_INVOICE_FROM_QUOTE = 'billing-subject_invoice_from_quote'
REL_OBJ_INVOICE_FROM_QUOTE = 'billing-object_invoice_from_quote'

DEFAULT_HFILTER_INVOICE  = 'billing-hf_invoice'
DEFAULT_HFILTER_QUOTE    = 'billing-hf_quote'
DEFAULT_HFILTER_ORDER    = 'billing-hf_salesorder'
DEFAULT_HFILTER_CNOTE    = 'billing-hf_creditnote'
DEFAULT_HFILTER_TEMPLATE = 'billing-hf_template'
DEFAULT_HFILTER_PLINE    = 'billing-hg_product_lines'  # TODO: fix "hf" + singular
DEFAULT_HFILTER_SLINE    = 'billing-hg_service_lines'

DEFAULT_QUANTITY = Decimal('1.00')

# UUIDs ---
UUID_CNOTE_STATUS_DRAFT = '57191226-8ece-4a7d-bb5f-1b9635f41d9b'

UUID_INVOICE_STATUS_DRAFT      = '1bbb7c7e-610f-4366-b3de-b92d63c9cf23'
UUID_INVOICE_STATUS_TO_BE_SENT = 'cc1209bb-e8a2-40bb-9361-4230d9e27bf2'

UUID_ORDER_STATUS_ISSUED = 'bebdab5a-0281-4b34-a257-26602a19e320'

UUID_PAYMENT_TERMS_DEPOSIT = '86b76130-4cac-4337-95ff-3e9021329956'

UUID_WORKFLOW_QUOTE_ORGA_TO_PROSPECT      = 'a6a8f398-4967-49f8-8d8f-4aece55329fa'
UUID_WORKFLOW_QUOTE_CONTACT_TO_PROSPECT   = '81a52347-4988-4a11-81dc-55eca701447e'
UUID_WORKFLOW_INVOICE_ORGA_TO_CUSTOMER    = '3cc968ec-23c2-4f70-9609-1894d91ff300'
UUID_WORKFLOW_INVOICE_CONTACT_TO_CUSTOMER = '457f762d-0bd7-41de-8215-14585e3002ba'
