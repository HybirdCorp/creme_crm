# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def remove_old_ctypes(apps, schema_editor):
    filter_ct = apps.get_model('contenttypes', 'ContentType').objects.filter
    filter_ct(app_label='creme_core', model='teamm2m').delete()
    filter_ct(app_label='auth', model='user').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0012_v1_6__ct_one2one'),
    ]

    operations = [
        migrations.RunPython(remove_old_ctypes),
    ]
