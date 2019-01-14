# -*- coding: utf-8 -*-

from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.0')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0050_v2_0__relations_uniqueness_2'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
