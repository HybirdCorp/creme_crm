# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mimetypes import guess_type

from django.conf import settings
from django.db import migrations


def set_mime_types(apps, schema_editor):
    if settings.DOCUMENTS_DOCUMENT_MODEL != 'documents.Document':
        return

    get_model = apps.get_model
    MimeType = get_model('documents', 'MimeType')

    for doc in get_model('documents', 'Document').objects.filter(mime_type=None):
        mime_name = guess_type(doc.filedata.name)[0]

        if mime_name is not None:
            doc.mime_type = MimeType.objects.get_or_create(name=mime_name)[0]
            doc.save()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0010_v1_7__mime_type_1'),
    ]

    operations = [
        migrations.RunPython(set_mime_types),
    ]
