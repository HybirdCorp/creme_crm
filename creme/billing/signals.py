# -*- coding: utf-8 -*-

from logging import debug

#from django.dispatch import receiver #Django 1.3
from django.db.models.signals import post_save, post_delete

from creme import form_post_save
#@receiver(form_post_save) #Django 1.3
from creme_core.models.relation import Relation

from billing.models import ProductLine, ServiceLine
from billing.constants import REL_SUB_HAS_LINE, REL_SUB_LINE_RELATED_ITEM, REL_SUB_CREDIT_NOTE_APPLIED

def line_save(sender, instance, created, **kwargs):
    """Invoice calculated totals have to be refreshed

    """
    if instance.related_document is not None:
        instance.related_document.get_real_entity().save()

def connect_to_signals():
    form_post_save.connect (line_save, sender=ProductLine)
    form_post_save.connect (line_save, sender=ServiceLine)
    post_save.connect(line_relation,   sender=Relation)
    post_delete.connect(line_relation, sender=Relation)

def line_relation(sender, instance, **kwargs):
    """Billing models have a cache, so we have to invalidate the cache when a Line is "added" (Opportunity too?)
       Line models have to have only one relation between them and their related Product (or Service)
    """
    if instance.type_id == REL_SUB_HAS_LINE:
        document = instance.subject_entity
        document.get_real_entity().invalidate_cache()
        Relation.objects.filter(type=REL_SUB_HAS_LINE, object_entity=instance.object_entity, subject_entity=document).exclude(id=instance.pk).delete()
        debug("Cache invalidated for entity with pk: %s" % document.pk)

    elif instance.type_id == REL_SUB_LINE_RELATED_ITEM:
        Relation.objects.filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=instance.object_entity, subject_entity=instance.subject_entity).exclude(id=instance.pk).delete()

    elif instance.type_id == REL_SUB_CREDIT_NOTE_APPLIED:
        instance.object_entity.get_real_entity().save()