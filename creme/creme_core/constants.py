# import warnings
from decimal import Decimal

from django.conf import settings

# Auth ---
ROOT_USERNAME = ROOT_PASSWORD = 'root'  # TODO: in populate.py instead
UUID_SANDBOX_SUPERUSERS = '83c94e2a-8836-43a4-81b4-996627ef93aa'

# Relationships ---
REL_SUB_HAS = 'creme_core-subject_has'
REL_OBJ_HAS = 'creme_core-object_has'

# Setting keys ---
SETTING_BRICK_DEFAULT_STATE_IS_OPEN           = 'creme_core-default_block_state_is_open'
SETTING_BRICK_DEFAULT_STATE_SHOW_EMPTY_FIELDS = 'creme_core-default_block_state_show_empty_fields'

# Notification ---
UUID_CHANNEL_SYSTEM    = '5d536e3a-eee9-46e2-81c2-2e40cde9e87c'
UUID_CHANNEL_ADMIN     = 'bd008630-0c5b-463f-8b21-d0d7d1c442b3'
UUID_CHANNEL_JOBS      = '0ef8c336-671f-4777-aa71-9f5af2e8b963'
UUID_CHANNEL_REMINDERS = 'b52ea0d1-6ce5-43c5-87b0-40845671b916'

# Bricks ---
MODELBRICK_ID = 'model'

# Money money money ---
DEFAULT_VAT = Decimal(getattr(settings, 'DEFAULT_VAT', '20.0'))  # TODO: depends on country...


# def __getattr__(name):
#     if name == 'DEFAULT_CURRENCY_PK':
#         warnings.warn(
#             '"DEFAULT_CURRENCY_PK" is deprecated; '
#             'use Currency.objects.default().id instead.',
#             DeprecationWarning,
#         )
#         return 1
#
#     if name == 'DISPLAY_CURRENCY_LOCAL_SYMBOL':
#         warnings.warn(
#             '"DISPLAY_CURRENCY_LOCAL_SYMBOL" is deprecated; '
#             'use creme_core.setting_keys.currency_symbol_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'creme_core-display_currency_local_symbol'
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
