# -*- coding: utf-8 -*-

from django.db import migrations


def remove_sessions(apps, schema_editor):
    apps.get_model('sessions', 'Session').objects.all().delete()


def set_version(apps, schema_editor):
    apps.get_model('creme_core', 'Version').objects.create(value='2.3')


class Migration(migrations.Migration):
    dependencies = [
        ('sessions', '0001_initial'),
        ('creme_core', '0090_v2_3__rm_upload_prefix'),
    ]

    operations = [
        migrations.RunPython(remove_sessions),
        migrations.RunPython(set_version),
    ]
