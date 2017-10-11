# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FolderCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Category name')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Folder category',
                'verbose_name_plural': 'Folder categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('title', models.CharField(unique=True, max_length=100, verbose_name='Title')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('category', models.ForeignKey(related_name='folder_category_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Category', blank=True, to='documents.FolderCategory', null=True)),
                #('parent_folder', models.ForeignKey(related_name='parent_folder_set', verbose_name='Parent folder', blank=True, to='documents.Folder', null=True)),
                ('parent_folder', models.ForeignKey(related_name='parent_folder_set', verbose_name='Parent folder', blank=True, to=settings.DOCUMENTS_FOLDER_MODEL, null=True)),
            ],
            options={
                'swappable': 'DOCUMENTS_FOLDER_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Folder',
                'verbose_name_plural': 'Folders',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('title', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('filedata', models.FileField(upload_to=b'upload/documents', max_length=500, verbose_name='File')),
                ('folder', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Folder', to=settings.DOCUMENTS_FOLDER_MODEL)),
            ],
            options={
                'swappable': 'DOCUMENTS_DOCUMENT_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Document',
                'verbose_name_plural': 'Documents',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
