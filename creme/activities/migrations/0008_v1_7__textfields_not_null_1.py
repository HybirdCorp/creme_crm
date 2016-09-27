# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def fill_none_strings(apps, schema_editor):
    if settings.ACTIVITIES_ACTIVITY_MODEL == 'activities.Activity':
        Activity = apps.get_model('activities', 'Activity')

        Activity.objects.filter(description=None).update(description='')
        Activity.objects.filter(minutes=None).update(minutes='')


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0007_v1_7__charfields_not_nullable_2'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
