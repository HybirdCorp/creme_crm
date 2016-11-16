# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0004_v1_7__textfields_not_null_2'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Document category',
                'verbose_name_plural': 'Document categories',
            },
        ),
        migrations.AddField(
            model_name='document',
            name='categories',
            field=models.ManyToManyField(to='documents.DocumentCategory', verbose_name='Categories', blank=True),
        ),
    ]
