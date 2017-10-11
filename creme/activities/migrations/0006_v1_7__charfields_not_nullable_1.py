# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.db.models import Q

# NB: it seems PostGreSQL does like that we migrate CharFields directly
#     (ie: only '0007_v1_7__charfields_not_null_2.py')


def fill_none_strings(apps, schema_editor):
    get_model = apps.get_model

    if settings.ACTIVITIES_ACTIVITY_MODEL == 'activities.Activity':
        get_model('activities.Activity').objects.filter(place__isnull=True).update(place='')

    get_model('activities.Calendar').objects.filter(Q(color__isnull=True)|Q(color='')) \
                                            .update(color='ff0000')


class Migration(migrations.Migration):
    dependencies = [
        # ('activities', '0005_v1_6__field_place_is_longer'),
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
