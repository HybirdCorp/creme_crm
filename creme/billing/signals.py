# -*- coding: utf-8 -*-

#from django.dispatch import receiver #Django 1.3

from creme import form_post_save

from billing.models import ProductLine, ServiceLine

#@receiver(form_post_save) #Django 1.3
def line_save(sender, instance, created, **kwargs):
    """Invoice calculated totals have to be refreshed

    """

    if instance.document is not None:
        instance.document.get_real_entity().save()

def connect_to_signals():
    form_post_save.connect (line_save, sender=ProductLine)
    form_post_save.connect (line_save, sender=ServiceLine)