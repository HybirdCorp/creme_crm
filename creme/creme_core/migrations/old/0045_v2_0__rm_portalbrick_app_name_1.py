# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def delete_portals_locations(apps, schema_editor):
    apps.get_model('creme_core', 'BlockPortalLocation')\
        .objects \
        .exclude(app_name='creme_core')\
        .delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0044_v2_0__rm_pref_menu_item'),
    ]

    operations = [
        migrations.RunPython(delete_portals_locations),
    ]
