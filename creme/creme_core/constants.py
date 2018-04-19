# -*- coding: utf-8 -*-

from decimal import Decimal

from django.conf import settings


DEFAULT_VAT = Decimal(getattr(settings, 'DEFAULT_VAT', '20.0'))  # TODO: depends on country...

# PROP_IS_MANAGED_BY_CREME = 'creme_core-is_managed_by_creme'

REL_SUB_HAS = 'creme_core-subject_has'
REL_OBJ_HAS = 'creme_core-object_has'

SETTING_BRICK_DEFAULT_STATE_IS_OPEN           = 'creme_core-default_block_state_is_open'
SETTING_BRICK_DEFAULT_STATE_SHOW_EMPTY_FIELDS = 'creme_core-default_block_state_show_empty_fields'
SETTING_BLOCK_DEFAULT_STATE_IS_OPEN           = SETTING_BRICK_DEFAULT_STATE_IS_OPEN            # DEPRECATED
SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS = SETTING_BRICK_DEFAULT_STATE_SHOW_EMPTY_FIELDS  # DEPRECATED

UUID_SANDBOX_SUPERUSERS = '83c94e2a-8836-43a4-81b4-996627ef93aa'

DEFAULT_CURRENCY_PK = 1
DISPLAY_CURRENCY_LOCAL_SYMBOL = 'creme_core-display_currency_local_symbol'

MODELBLOCK_ID = 'modelblock'

# ICON_SIZE_MAP = {
#         'big':    64,
#         'normal': 48,
#         'medium': 32,
#         'small':  22,
#         'tiny':   16,
#     }
