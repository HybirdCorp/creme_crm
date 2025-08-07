import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

from creme.creme_core.models import CREME_REPLACE_NULL


class Migration(migrations.Migration):
    # replaces = [
    #     ('documents', '0001_initial'),
    #     ('documents', '0020_v2_4__minion_categories01'),
    #     ('documents', '0021_v2_4__minion_categories02'),
    #     ('documents', '0022_v2_4__minion_categories03'),
    # ]

    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FolderCategory',
            fields=[
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    ),
                ),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Category name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('title', models.CharField(max_length=100, verbose_name='Title')),
                (
                    'category',
                    models.ForeignKey(
                        to='documents.FolderCategory',
                        verbose_name='Category',
                        on_delete=CREME_REPLACE_NULL, null=True, blank=True,
                        related_name='folder_category_set',
                        help_text="The parent's category will be copied if you do not select one.",
                    ),
                ),
                (
                    'parent_folder',
                    models.ForeignKey(
                        to=settings.DOCUMENTS_FOLDER_MODEL,
                        verbose_name='Parent folder',
                        null=True, blank=True,
                        related_name='children', on_delete=PROTECT,
                    ),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True, editable=False)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
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
                (
                    'id',
                    models.AutoField(
                        verbose_name='ID', serialize=False, auto_created=True, primary_key=True,
                    )
                ),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('title', models.CharField(max_length=100, verbose_name='Name', blank=True)),
                (
                    'filedata',
                    models.FileField(
                        verbose_name='File', upload_to='documents', max_length=500,
                    ),
                ),
                (
                    'linked_folder',
                    models.ForeignKey(
                        to=settings.DOCUMENTS_FOLDER_MODEL,
                        on_delete=PROTECT, verbose_name='Folder',
                    ),
                ),
                (
                    'categories',
                    models.ManyToManyField(
                        to='documents.DocumentCategory', verbose_name='Categories', blank=True,
                    ),
                ),
                (
                    'mime_type',
                    models.ForeignKey(
                        to='documents.MimeType', null=True, on_delete=PROTECT,
                        editable=False, verbose_name='MIME type',
                    ),
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
