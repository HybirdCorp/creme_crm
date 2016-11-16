# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0009_v1_7__image_to_doc_4'),
    ]

    operations = [
        migrations.CreateModel(
            name='MimeType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'MIME type',
                'verbose_name_plural': 'MIME types',
            },
        ),
        migrations.AddField(
            model_name='document',
            name='mime_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, editable=False,
                                    to='documents.MimeType', null=True, verbose_name='MIME type',
                                   ),
        ),
    ]
