# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0034_v1_8__rm_settingvalue_user'),
    ]

    operations = [
        migrations.RenameField(
            model_name='blockdetailviewlocation',
            old_name='block_id',
            new_name='brick_id',
        ),
        migrations.RenameField(
            model_name='blockmypagelocation',
            old_name='block_id',
            new_name='brick_id',
        ),
        migrations.RenameField(
            model_name='blockportallocation',
            old_name='block_id',
            new_name='brick_id',
        ),
        migrations.RenameField(
            model_name='blockstate',
            old_name='block_id',
            new_name='brick_id',
        ),
        migrations.RenameField(
            model_name='instanceblockconfigitem',
            old_name='block_id',
            new_name='brick_id',
        ),
        migrations.RenameField(
            model_name='relationblockitem',
            old_name='block_id',
            new_name='brick_id',
        ),
        migrations.AlterUniqueTogether(
            name='blockstate',
            unique_together={('user', 'brick_id')},
        ),
    ]
