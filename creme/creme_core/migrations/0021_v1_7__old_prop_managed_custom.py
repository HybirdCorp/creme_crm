# -*- coding: utf-8 -*-

from django.db import migrations

PROP_IS_MANAGED_BY_CREME = 'creme_core-is_managed_by_creme'


def set_old_managed_custom(apps, schema_editor):
    apps.get_model('creme_core', 'CremePropertyType') \
        .objects \
        .filter(id=PROP_IS_MANAGED_BY_CREME) \
        .update(is_custom=True)


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0020_v1_7__properties_uniqueness_2'),
    ]

    operations = [
        migrations.RunPython(set_old_managed_custom),
    ]
