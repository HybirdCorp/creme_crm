# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model("creme_core", "Version").objects.create(value='1.6')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0013_v1_6__clean_ctypes'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
