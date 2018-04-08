# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Q


def rbi_set_default_cells(apps, schema_editor):
    apps.get_model('creme_core', 'RelationBlockItem')\
        .objects.filter(Q(json_cells_map='') | Q(json_cells_map=None))\
        .update(json_cells_map='{}')


def cbi_set_default_cells(apps, schema_editor):
    apps.get_model('creme_core', 'CustomBlockConfigItem')\
        .objects.filter(Q(json_cells='') | Q(json_cells=None))\
        .update(json_cells='[]')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0035_v1_8__block_id_2_brick_id'),
    ]

    operations = [
        migrations.RunPython(rbi_set_default_cells),
        migrations.RunPython(cbi_set_default_cells),
    ]
