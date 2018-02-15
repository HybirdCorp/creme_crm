# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def fill_none_strings(apps, schema_editor):
    get_model = apps.get_model

    get_model('sms.Recipient').objects.filter(phone__isnull=True).update(phone='')
    get_model('sms.Message').objects.filter(status_message__isnull=True).update(status_message='')


class Migration(migrations.Migration):
    dependencies = [
        ('sms', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
