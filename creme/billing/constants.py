# -*- coding: utf-8 -*-

from decimal import Decimal, ROUND_UP, ROUND_DOWN, ROUND_HALF_EVEN
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

DEFAULT_DECIMAL = Decimal()
DEFAULT_VAT = Decimal(getattr(settings, "DEFAULT_VAT", "19.6"))
ROUND_POLICY = ROUND_UP
CURRENCY = "Euro"

REL_SUB_BILL_ISSUED = 'billing-subject_bill_issued'
REL_OBJ_BILL_ISSUED = 'billing-object_bill_issued'

REL_SUB_BILL_RECEIVED = 'billing-subject_bill_received'
REL_OBJ_BILL_RECEIVED = 'billing-object_bill_received'

REL_SUB_HAS_LINE = 'billing-subject_had_line'
REL_OBJ_HAS_LINE = 'billing-object_had_line'

REL_SUB_LINE_RELATED_ITEM = 'billing-subject_line_related_item'
REL_OBJ_LINE_RELATED_ITEM = 'billing-object_line_related_item'

DEFAULT_DRAFT_INVOICE_STATUS = 1
DEFAULT_INVOICE_STATUS = 2

DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA = 'billing-display_payment_info_only_creme_orga'

PERCENT_PK = 1
AMOUNT_PK  = 2

DISCOUNT_UNIT = {PERCENT_PK: _(u"Percent"),
                 AMOUNT_PK:  _(u"Amount"),
                }

