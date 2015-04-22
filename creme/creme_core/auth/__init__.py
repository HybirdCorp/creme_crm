from .entity_credentials import EntityCredentials


def build_creation_perm(model):
    return '%s.add_%s' % (model._meta.app_label, model.__name__.lower())

