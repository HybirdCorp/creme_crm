# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations

PROP_IS_MANAGED_BY_CREME = 'creme_core-is_managed_by_creme'


def convert_old__managed_organisations(apps, schema_editor):
    if settings.PERSONS_ORGANISATION_MODEL == 'persons.Organisation':
        updated = apps.get_model('persons', 'Organisation') \
                      .objects \
                      .filter(properties__type=PROP_IS_MANAGED_BY_CREME) \
                      .update(is_managed=True)

        if updated:
            print('The way the managed Organisations are stored has changed ; '
                  'it is now a field, & not a property anymore. '
                  'You will have to update the custom block which displays the '
                  'Organisations information if you want to see this field.'
                 )


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0017_v1_7__organisation_managed_1'),
    ]

    operations = [
        migrations.RunPython(convert_old__managed_organisations),
    ]
