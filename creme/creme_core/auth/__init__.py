from .entity_credentials import EntityCredentials  # NOQA

# NB: with '*' there cannot be collision with app label
SUPERUSER_PERM = '*superuser*'
STAFF_PERM     = '*staff*'

_CREATION_PREFIX = 'add_'
_LINK_PREFIX = 'link_'
_EXPORT_PREFIX = 'export_'


def build_creation_perm(model):
    # return f'{model._meta.app_label}.add_{model.__name__.lower()}'
    return f'{model._meta.app_label}.{_CREATION_PREFIX}{model.__name__.lower()}'


def build_link_perm(model):
    # return f'{model._meta.app_label}.link_{model.__name__.lower()}'
    return f'{model._meta.app_label}.{_LINK_PREFIX}{model.__name__.lower()}'
