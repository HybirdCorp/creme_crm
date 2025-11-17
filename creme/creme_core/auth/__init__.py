from .entity_credentials import EntityCredentials  # NOQA

# NB: with '*' there cannot be collision with app label
SUPERUSER_PERM = '*superuser*'
STAFF_PERM     = '*staff*'

_SPECIAL_PREFIX = 'special#'

# Model permissions
_CREATION_PREFIX = 'add_'
_LINK_PREFIX = 'link_'
_LIST_PREFIX = 'list_'
_EXPORT_PREFIX = 'export_'


def __build_model_perm(model, prefix):
    return f'{model._meta.app_label}.{prefix}{model.__name__.lower()}'


def build_creation_perm(model):
    return __build_model_perm(model, prefix=_CREATION_PREFIX)


def build_link_perm(model):
    return __build_model_perm(model, prefix=_LINK_PREFIX)


def build_list_perm(model):
    return __build_model_perm(model, prefix=_LIST_PREFIX)


def build_export_perm(model):
    return __build_model_perm(model, prefix=_EXPORT_PREFIX)
