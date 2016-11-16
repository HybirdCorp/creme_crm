# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import fsync
from shutil import copyfileobj

from django.conf import settings
from django.db import migrations


def copy_images_files(apps, schema_editor):
    if settings.DOCUMENTS_FOLDER_MODEL != 'documents.Folder':
        return

    for doc in apps.get_model('documents', 'Document').objects.exclude(filedata_tmp__isnull=True):
        dest = doc.filedata.path

        with open(doc.filedata_tmp.path, 'rb') as fsrc:
            with open(dest, 'wb') as fdst:
                copyfileobj(fsrc, fdst)
                fdst.flush()
                fsync(fdst.fileno())

        doc.filedata_tmp = None
        doc.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0007_v1_7__image_to_doc_2'),
    ]

    operations = [
        migrations.RunPython(copy_images_files),
    ]
