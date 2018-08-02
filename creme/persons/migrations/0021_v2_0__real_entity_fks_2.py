# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import F


def fill_entity_fks(apps, schema_editor):
    apps.get_model('persons', 'Address').objects.update(object_id=F('old_object_id'))


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0020_v2_0__real_entity_fks_1'),
    ]

    operations = [
        migrations.RunPython(fill_entity_fks),
    ]
