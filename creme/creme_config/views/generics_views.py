import warnings

from .generics import *  # NOQA

warnings.warn(
    "The module 'generics_views' is deprecated; use 'generics' instead",
    DeprecationWarning
)
