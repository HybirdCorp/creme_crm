# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def fix_header_filters(apps, schema_editor):
    apps.get_model('creme_core', 'HeaderFilter')\
        .objects.exclude(id__startswith='creme_core-userhf_')\
                .update(is_custom=False)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0031_v1_7__cremeentity_uuid_3'),
    ]

    operations = [
        migrations.RunPython(fix_header_filters),
    ]
