# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def fill_none_reference(apps, schema_editor):
    if settings.OPPORTUNITIES_OPPORTUNITY_MODEL == 'opportunities.Opportunity':
        apps.get_model('opportunities', 'Opportunity').objects.filter(reference__isnull=True).update(reference='')


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_reference),
    ]
