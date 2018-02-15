# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_v1_7__charfields_not_nullable_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='web_site',
            field=models.CharField(default='', max_length=100, verbose_name='Web Site', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='service',
            name='web_site',
            field=models.CharField(default='', max_length=100, verbose_name='Web Site', blank=True),
            preserve_default=False,
        ),
    ]
