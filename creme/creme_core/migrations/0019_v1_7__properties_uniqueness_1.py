# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Count


def remove_duplicated_properties(apps, schema_editor):
    get_model = apps.get_model
    CremeProperty = get_model('creme_core', 'CremeProperty')
    CremeEntity = get_model('creme_core', 'CremeEntity')

    for prop_type_id in get_model('creme_core', 'CremePropertyType').objects.values_list('id', flat=True):
        for e_id in CremeEntity.objects.filter(properties__type=prop_type_id) \
                                       .annotate(prop_count=Count('properties')) \
                                       .filter(prop_count__gte=2) \
                                       .values_list('id', flat=True):
            for prop in CremeProperty.objects.filter(creme_entity=e_id, type=prop_type_id)[1:]:
                prop.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0018_v1_7__cremeuser_settings'),
    ]

    operations = [
        migrations.RunPython(remove_duplicated_properties),
    ]
