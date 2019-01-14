# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('crudity', '0006_v2_0__waction_binary_data02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='waitingaction',
            name='raw_data',
        ),
        migrations.RenameField(
                model_name='waitingaction',
                old_name='raw_data_tmp',
                new_name='raw_data',
        ),
    ]
