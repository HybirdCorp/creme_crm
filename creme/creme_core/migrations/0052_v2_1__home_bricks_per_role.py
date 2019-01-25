# -*- coding: utf-8 -*-

from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='brickhomelocation',
            name='role',
            field=models.ForeignKey(default=None, null=True, on_delete=CASCADE, to='creme_core.UserRole', verbose_name='Related role'),
        ),
        migrations.AddField(
            model_name='brickhomelocation',
            name='superuser',
            field=models.BooleanField(default=False, editable=False, verbose_name='related to superusers'),
        ),
    ]
