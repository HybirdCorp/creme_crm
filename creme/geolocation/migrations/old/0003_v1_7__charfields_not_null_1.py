# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

# NB: it seems PostGreSQL does like that we migrate CharFields directly
#     (ie: only '0004_v1_7__charfields_not_null_2.py')

TOWN_FIELDS = ['country', 'zipcode']


def fill_none_strings(apps, schema_editor):
    manager = apps.get_model('geolocation', 'Town').objects

    for field_name in TOWN_FIELDS:
        manager.filter(**{field_name: None}).update(**{field_name: ''})


class Migration(migrations.Migration):
    dependencies = [
        # ('geolocation', '0002_v1_6__fix_block_ids'),
        ('geolocation', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
