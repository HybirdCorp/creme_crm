# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def fill_none_name(apps, schema_editor):
    if settings.RECURRENTS_RGENERATOR_MODEL == 'recurrents.RecurrentGenerator':
        apps.get_model('recurrents', 'RecurrentGenerator').objects.filter(name__isnull=True).update(name='')


class Migration(migrations.Migration):
    dependencies = [
        ('recurrents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_name),
    ]
