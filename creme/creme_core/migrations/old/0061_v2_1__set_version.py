# -*- coding: utf-8 -*-

from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.1')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0060_v2_1__credentials_with_filter'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
