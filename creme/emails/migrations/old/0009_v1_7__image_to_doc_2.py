# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def replace_signature_img_m2m(apps, schema_editor):
    for signature in apps.get_model('emails', 'EmailSignature').objects.filter(images__isnull=False):
        signature.images_tmp = list(signature.images.values_list('id', flat=True))


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0008_v1_7__image_to_doc_1'),
    ]

    operations = [
        migrations.RunPython(replace_signature_img_m2m),
    ]
