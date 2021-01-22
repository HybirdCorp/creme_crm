# -*- coding: utf-8 -*-

from django.db import migrations


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.2')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0076_v2_2__cremeuser_language'),
    ]

    operations = [
        migrations.RunPython(set_version),
    ]
