# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def fill_none_name(apps, schema_editor):
    if settings.RECURRENTS_RGENERATOR_MODEL == 'recurrents.RecurrentGenerator':
        apps.get_model('recurrents', 'RecurrentGenerator').objects.filter(description__isnull=True) \
                                                                  .update(description='')


class Migration(migrations.Migration):
    dependencies = [
        ('recurrents', '0003_v1_7__name_not_null_2'),
    ]

    operations = [
        migrations.RunPython(fill_none_name),
    ]
