# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations  # models
from django.conf import settings

from creme.documents.models.fields import ImageEntityManyToManyField


class Migration(migrations.Migration):
    dependencies = [
        # migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
        ('documents', '0007_v1_7__image_to_doc_2'),
        ('products', '0004_v1_7__charfields_not_nullable_2'),
    ]

    operations = [
        # migrations.AddField(
        #     model_name='product',
        #     name='images_tmp',
        #     field=models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Images', blank=True),
        # ),
        # migrations.AddField(
        #     model_name='service',
        #     name='images_tmp',
        #     field=models.ManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Images', blank=True),
        # ),
        migrations.AddField(
            model_name='product',
            name='images_tmp',
            field=ImageEntityManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Images', blank=True),
        ),
        migrations.AddField(
            model_name='service',
            name='images_tmp',
            field=ImageEntityManyToManyField(to=settings.DOCUMENTS_DOCUMENT_MODEL, verbose_name='Images', blank=True),
        ),
    ]
