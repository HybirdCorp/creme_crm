# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import F


def fill_entity_fks(apps, schema_editor):
    get_model = apps.get_model

    for model_name in ('Action', 'Alert', 'Memo', 'ToDo', 'UserMessage'):
        get_model('assistants', model_name).objects.update(entity_id=F('old_entity_id'))


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0006_v2_0__real_entity_fks_1'),
    ]

    operations = [
        migrations.RunPython(fill_entity_fks),
    ]
