# -*- coding: utf-8 -*-

from json import dumps as json_dump
from pickle import loads as pickle_load

from django.db import migrations


def fill_json(apps, schema_editor):
    for lwemail in apps.get_model('emails', 'LightWeightEmail').objects.all():
        body = lwemail.body

        if body:
            # lwemail.body = b''
            lwemail.body_tmp = json_dump(pickle_load(body.encode(), encoding='utf-8'))
            lwemail.save()


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0012_v2_0__lwmail_body_json01'),
    ]

    operations = [
        migrations.RunPython(fill_json),
    ]
