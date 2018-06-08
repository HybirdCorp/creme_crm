# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0047_v2_0__rename_bricks_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relation',
            name='symmetric_relation',
            field=models.ForeignKey(null=True, on_delete=CASCADE, to='creme_core.Relation'),
        ),
        migrations.AlterField(
            model_name='relation',
            name='type',
            field=models.ForeignKey(default='placeholder', on_delete=CASCADE, to='creme_core.RelationType'),
            preserve_default=False,
        ),
    ]
