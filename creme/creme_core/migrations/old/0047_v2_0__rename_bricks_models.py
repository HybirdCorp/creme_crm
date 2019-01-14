# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0046_v2_0__rm_portalbrick_app_name_2'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BlockDetailviewLocation',
            new_name='BrickDetailviewLocation',
        ),
        migrations.RenameModel(
            old_name='BlockPortalLocation',
            new_name='BrickHomeLocation',
        ),
        migrations.RenameModel(
            old_name='BlockMypageLocation',
            new_name='BrickMypageLocation',
        ),
        migrations.RenameModel(
            old_name='BlockState',
            new_name='BrickState',
        ),
        migrations.RenameModel(
            old_name='InstanceBlockConfigItem',
            new_name='InstanceBrickConfigItem',
        ),
        migrations.RenameModel(
            old_name='CustomBlockConfigItem',
            new_name='CustomBrickConfigItem',
        ),
        migrations.RenameModel(
            old_name='RelationBlockItem',
            new_name='RelationBrickItem',
        ),
    ]
