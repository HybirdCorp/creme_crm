# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations

# NB: it seems PostGreSQL does like that we migrate CharFields directly
#     (ie: only '0009_v1_7__charfields_not_nullable_2.py')

CONTACT_FIELDS = ['first_name', 'description', 'skype', 'phone', 'mobile', 'email', 'url_site', 'full_position']
ORGANISATION_FIELDS = ['description', 'phone', 'fax', 'email', 'url_site', 'annual_revenue', 'siren', 'naf', 'siret', 'rcs', 'tvaintra']
ADDRESS_FIELDS = ['name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country']


def fill_none_strings(apps, schema_editor):
    def migrate_model(setting_model, name, fields):
        if setting_model == 'persons.%s' % name:
            manager = apps.get_model('persons', name).objects

            for field_name in fields:
                manager.filter(**{field_name: None}).update(**{field_name: ''})

    migrate_model(settings.PERSONS_CONTACT_MODEL,      'Contact',      CONTACT_FIELDS)
    migrate_model(settings.PERSONS_ORGANISATION_MODEL, 'Organisation', ORGANISATION_FIELDS)
    migrate_model(settings.PERSONS_ADDRESS_MODEL,      'Address',      ADDRESS_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0007_v1_6__rm_address_relnames'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
