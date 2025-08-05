# import warnings
from django.utils.translation import gettext_lazy as _

from .core.setting_key import SettingKey

global_filters_edition_key = SettingKey(
    id='creme_core-global_filters_edition',
    description=_(
        'Filters & views of list without owner can be edited by all users? '
        '("No" means only superusers are allowed to)'
    ),
    app_label='creme_core', type=SettingKey.BOOL,
)
brick_opening_key = SettingKey(
    id='creme_core-default_block_state_is_open',  # TODO: rename with "brick"
    description=_('By default, are blocks open?'),
    app_label='creme_core', type=SettingKey.BOOL,
)
brick_showempty_key = SettingKey(
    id='creme_core-default_block_state_show_empty_fields',  # TODO: rename with "brick"
    description=_('By default, are empty fields displayed?'),
    app_label='creme_core', type=SettingKey.BOOL,
)
currency_symbol_key = SettingKey(
    id='creme_core-display_currency_local_symbol',
    description=_(
        'Display the currency local symbol (e.g. €)? '
        'If no the international symbol will be used (ex: EUR)'
    ),
    app_label='creme_core', type=SettingKey.BOOL,
)


# def __getattr__(name):
#     if name == 'block_opening_key':
#         warnings.warn(
#             '"block_opening_key" is deprecated; '
#             'use creme_core.setting_keys.brick_opening_key instead.',
#             DeprecationWarning,
#         )
#         return brick_opening_key
#
#     if name == 'block_showempty_key':
#         warnings.warn(
#             '"block_showempty_key" is deprecated; '
#             'use creme_core.setting_keys.brick_showempty_key instead.',
#             DeprecationWarning,
#         )
#         return brick_showempty_key
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
