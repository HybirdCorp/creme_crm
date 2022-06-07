from django.contrib.contenttypes.models import ContentType

from creme.creme_core.registry import creme_registry


def get_cremeentity_contenttypes():
    models = list(creme_registry.iter_entity_models())
    return ContentType.objects.get_for_models(*models).values()


def get_cremeentity_contenttype_queryset():
    content_types = get_cremeentity_contenttypes()
    ct_queryset = ContentType.objects.filter(pk__in=[ct.id for ct in content_types])
    return ct_queryset
