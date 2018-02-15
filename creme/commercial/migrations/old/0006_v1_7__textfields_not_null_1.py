# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


ACT_FIELDS = ['goal']
APPROACH_FIELDS = ['description']
SEGMENT_DESCRIPTION__FIELDS = ['product', 'place', 'price', 'promotion']


def fill_none_strings(apps, schema_editor):
    def migrate_model(name, fields):
        manager = apps.get_model('commercial', name).objects

        for field_name in fields:
            manager.filter(**{field_name: None}).update(**{field_name: ''})

    migrate_model('CommercialApproach',       APPROACH_FIELDS)
    migrate_model('MarketSegmentDescription', SEGMENT_DESCRIPTION__FIELDS)

    if settings.COMMERCIAL_ACT_MODEL == 'commercial.Act':
        migrate_model('Act', ACT_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0005_v1_7__is_job_enabled'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
