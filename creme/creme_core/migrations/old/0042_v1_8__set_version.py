# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='1.8')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0041_v1_8_is_actived'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
