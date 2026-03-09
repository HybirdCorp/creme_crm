import warnings

from creme.creme_core.core.validators import TemplateVariablesValidator  # NOQA

warnings.warn(
    'emails.core.validators is deprecated; use'
    'creme_core.core.validators.TemplateVariablesValidator instead',
    DeprecationWarning,
)
