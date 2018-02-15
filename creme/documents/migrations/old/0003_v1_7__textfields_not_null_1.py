# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def fill_none_strings(apps, schema_editor):
    def migrate_model(setting_model, name):
        if setting_model == 'documents.%s' % name:
            apps.get_model('documents', name).objects.filter(description=None).update(description='')

    migrate_model(settings.DOCUMENTS_FOLDER_MODEL,   'Folder')
    migrate_model(settings.DOCUMENTS_DOCUMENT_MODEL, 'Document')


class Migration(migrations.Migration):
    dependencies = [
        # ('documents', '0002_v1_6__folder_unicity_n_category_is_custom'),
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
