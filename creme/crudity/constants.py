# import warnings

# Used as a multiline delimiter. /!\ They have to have the same length
LEFT_MULTILINE_SEP  = '[['
RIGHT_MULTILINE_SEP = ']]'

# def __getattr__(name):
#     if name == 'SETTING_CRUDITY_SANDBOX_BY_USER':
#         warnings.warn(
#             '"SETTING_CRUDITY_SANDBOX_BY_USER" is deprecated; '
#             'use crudity.setting_keys.sandbox_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'crudity-crudity_sandbox_by_user'
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
