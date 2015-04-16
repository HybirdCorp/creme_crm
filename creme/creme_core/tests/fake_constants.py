# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

FAKE_REL_SUB_EMPLOYED_BY = 'creme_core-subject_fake_employed_by'
FAKE_REL_OBJ_EMPLOYED_BY = 'creme_core-object_fake_employed_by'

FAKE_REL_SUB_BILL_ISSUED = 'creme_core-subject_fake_bill_issued'
FAKE_REL_OBJ_BILL_ISSUED = 'creme_core-object_fake_bill_issued'

FAKE_REL_SUB_BILL_RECEIVED = 'creme_core-subject_fake_bill_received'
FAKE_REL_OBJ_BILL_RECEIVED = 'creme_core-object_fake_bill_received'

FAKE_PERCENT_UNIT = 1
FAKE_AMOUNT_UNIT  = 2
FAKE_DISCOUNT_UNIT = {FAKE_PERCENT_UNIT: _(u"Percent"),
                      FAKE_AMOUNT_UNIT:  _(u"Amount"),
                     }
