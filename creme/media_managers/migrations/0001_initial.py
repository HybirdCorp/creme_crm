# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of media category')),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Media category',
                'verbose_name_plural': 'Media categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, null=True, verbose_name='Name', blank=True)),
                ('description', models.TextField(max_length=500, null=True, verbose_name='Description', blank=True)),
                ('height', models.CharField(verbose_name='Height', max_length=50, null=True, editable=False, blank=True)),
                ('width', models.CharField(verbose_name='Width', max_length=50, null=True, editable=False, blank=True)),
                ('image', models.ImageField(height_field=b'height', upload_to=b'upload/images', width_field=b'width', max_length=500, verbose_name='Image')),
                ('categories', models.ManyToManyField(related_name='Image_media_category_set', verbose_name='Categories', to='media_managers.MediaCategory', blank=True)), # null=True
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Image',
                'verbose_name_plural': 'Images',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
