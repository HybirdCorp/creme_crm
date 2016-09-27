# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def fill_none_strings(apps, schema_editor):
    get_model = apps.get_model

    Action = get_model('assistants', 'Action')
    Action.objects.filter(description=None).update(description='')
    Action.objects.filter(expected_reaction=None).update(expected_reaction='')

    get_model('assistants', 'Alert').objects.filter(description=None).update(description='')

    get_model('assistants', 'ToDo').objects.filter(description=None).update(description='')

    Memo = get_model('assistants', 'Memo')
    Memo.objects.filter(content=None).update(content='?')
    Memo.objects.filter(content='').update(content='?')


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0002_v1_6__convert_user_FKs'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
