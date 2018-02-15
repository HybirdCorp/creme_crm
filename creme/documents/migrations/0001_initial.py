# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.conf import settings
from django.db import models, migrations
from django.db.models.deletion import SET_NULL, PROTECT


class Migration(migrations.Migration):
    # replaces = [
    #     (b'documents', '0001_initial'),
    #     (b'documents', '0003_v1_7__textfields_not_null_1'),
    #     (b'documents', '0004_v1_7__textfields_not_null_2'),
    #     (b'documents', '0005_v1_7__doc_categories'),
    #     (b'documents', '0006_v1_7__image_to_doc_1'),
    #     (b'documents', '0007_v1_7__image_to_doc_2'),
    #     (b'documents', '0008_v1_7__image_to_doc_3'),
    #     (b'documents', '0009_v1_7__image_to_doc_4'),
    #     (b'documents', '0010_v1_7__mime_type_1'),
    #     (b'documents', '0011_v1_7__mime_type_2'),
    #     (b'documents', '0012_v1_7__doc_categories_uniqueness'),
    #     (b'documents', '0013_v1_7__folders_uuids'),
    # ]

    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FolderCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Category name')),
                ('is_custom', models.BooleanField(default=True)),
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
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('category', models.ForeignKey(to='documents.FolderCategory',
                                               on_delete=SET_NULL, null=True, blank=True,
                                               related_name='folder_category_set',
                                               verbose_name='Category',
                                              )
                ),
                ('parent_folder', models.ForeignKey(to=settings.DOCUMENTS_FOLDER_MODEL, null=True,
                                                    blank=True, related_name='parent_folder_set', verbose_name='Parent folder',
                                                   )
                ),
            ],
            options={
                'swappable': 'DOCUMENTS_FOLDER_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Folder',
                'verbose_name_plural': 'Folders',
                'unique_together': {('title', 'parent_folder', 'category')},
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='DocumentCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True)),
            ],
            options={
                'ordering':            ('name',),
                'verbose_name':        'Document category',
                'verbose_name_plural': 'Document categories',
            },
        ),
        migrations.CreateModel(
            name='MimeType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
            ],
            options={
                'ordering':            ('name',),
                'verbose_name':        'MIME type',
                'verbose_name_plural': 'MIME types',
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('title', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('filedata', models.FileField(upload_to=b'upload/documents', max_length=500, verbose_name='File')),
                ('folder', models.ForeignKey(to=settings.DOCUMENTS_FOLDER_MODEL, on_delete=PROTECT, verbose_name='Folder')),
                ('categories', models.ManyToManyField(to='documents.DocumentCategory', verbose_name='Categories', blank=True)),
                ('mime_type', models.ForeignKey(to='documents.MimeType', null=True, on_delete=PROTECT,
                                                editable=False, verbose_name='MIME type',
                                               )
                ),
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
