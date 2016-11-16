# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def replace_ct_4_image(apps, schema_editor):
    get_model = apps.get_model
    ContentType = get_model('contenttypes', 'ContentType')

    ct_app_label, ct_model = settings.DOCUMENTS_FOLDER_MODEL.split('.')
    ct_doc = ContentType.objects.filter(app_label=ct_app_label, model=ct_model.lower()).first()

    if ct_doc is not None:
        ct_img = ContentType.objects.get(app_label='media_managers', model='image')

        get_model('commercial', 'CommercialApproach').objects.filter(entity_content_type=ct_img)\
                                                     .update(entity_content_type=ct_doc)


class Migration(migrations.Migration):
    dependencies = [
        ('documents',  '0007_v1_7__image_to_doc_2'),
        ('commercial', '0007_v1_7__textfields_not_null_2'),
    ]

    run_before = [
        ('documents',  '0009_v1_7__image_to_doc_4'),
    ]

    operations = [
        migrations.RunPython(replace_ct_4_image),
    ]
