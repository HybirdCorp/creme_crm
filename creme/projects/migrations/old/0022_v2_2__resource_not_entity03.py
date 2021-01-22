# -*- coding: utf-8 -*-

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0021_v2_2__resource_not_entity02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='tmp_id',
            field=models.PositiveIntegerField(default=1, unique=True),
        ),
        migrations.RemoveField(
            model_name='resource',
            name='cremeentity_ptr',
        ),
        migrations.AlterField(
            model_name='resource',
            name='tmp_id',
            field=models.PositiveIntegerField(
                default=1, unique=True, primary_key=True, serialize=False,
            ),
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='tmp_id',
            new_name='id',
        ),
        migrations.AlterField(
            model_name='resource',
            name='id',
            field=models.AutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
            ),
        ),
    ]
