# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('crudity', '0001_initial'),
    ]

    operations = [
        # migrations.AlterField(
        #     model_name='waitingaction',
        #     name='raw_data',
        #     field=models.BinaryField(blank=True, null=True),
        # ),
        migrations.AddField(
            model_name='waitingaction',
            name='raw_data_tmp',
            field=models.BinaryField(blank=True, null=True),
            preserve_default=False,
        ),
    ]
