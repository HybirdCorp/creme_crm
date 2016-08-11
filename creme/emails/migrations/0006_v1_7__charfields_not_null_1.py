# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


# NB: it seems PostGreSQL does like that we migrate CharFields directly
#     (ie: only '0007_v1_7__charfields_not_null_2.py')

RECIPIENT_FIELDS = ['address']
LW_EMAIL_FIELDS = ['subject']
E_EMAIL_FIELDS = ['subject']


def fill_none_strings(apps, schema_editor):
    def migrate_model(name, fields):
        manager = apps.get_model('emails', name).objects

        for field_name in fields:
            manager.filter(**{field_name: None}).update(**{field_name: ''})

    migrate_model('EmailRecipient', RECIPIENT_FIELDS)
    migrate_model('LightWeightEmail', LW_EMAIL_FIELDS)

    if settings.EMAILS_EMAIL_MODEL == 'emails.EntityEmail':
        migrate_model('EntityEmail', E_EMAIL_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0005_v1_6__custom_n_body_blocks'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
