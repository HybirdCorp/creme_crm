# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations  # models
from django.db.models.deletion import SET_NULL

from creme.documents.models.fields import ImageEntityForeignKey


class Migration(migrations.Migration):
    dependencies = [
        # migrations.swappable_dependency(settings.DOCUMENTS_DOCUMENT_MODEL),
        ('documents', '0007_v1_7__image_to_doc_2'),
        ('persons',   '0012_v1_7__fax_not_nullable_2'),
    ]

    operations = [
        # migrations.AddField(
        #     model_name='contact',
        #     name='image_tmp',
        #     field=models.ForeignKey(on_delete=SET_NULL, verbose_name='Photograph', blank=True, to=settings.DOCUMENTS_DOCUMENT_MODEL, null=True),
        # ),
        # migrations.AddField(
        #     model_name='organisation',
        #     name='image_tmp',
        #     field=models.ForeignKey(on_delete=SET_NULL, verbose_name='Logo', blank=True, to=settings.DOCUMENTS_DOCUMENT_MODEL, null=True),
        # ),
        migrations.AddField(
            model_name='contact',
            name='image_tmp',
            field=ImageEntityForeignKey(on_delete=SET_NULL, verbose_name='Photograph', blank=True, null=True,
                                        to=settings.DOCUMENTS_DOCUMENT_MODEL,  # TODO: remove in deconstruct ?
                                       ),
        ),
        migrations.AddField(
            model_name='organisation',
            name='image_tmp',
            field=ImageEntityForeignKey(on_delete=SET_NULL, verbose_name='Logo', blank=True, null=True,
                                        to=settings.DOCUMENTS_DOCUMENT_MODEL,
                                       ),
        ),
    ]
