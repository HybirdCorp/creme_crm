# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def fill_none_fax(apps, schema_editor):
    if settings.PERSONS_CONTACT_MODEL == 'persons.Contact':
        apps.get_model('persons', 'Contact').objects.filter(fax__isnull=True).update(fax='')


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0010_v1_7__lv_indexes'),
    ]

    operations = [
        migrations.RunPython(fill_none_fax),
    ]
