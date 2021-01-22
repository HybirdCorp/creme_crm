# -*- coding: utf-8 -*-

from django.db import migrations


def set_resource_ids(apps, schema_editor):
    for i, resource in enumerate(
        apps.get_model('projects', 'Resource').objects.order_by('cremeentity_ptr_id'),
        start=1,
    ):
        resource.tmp_id = i
        resource.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0020_v2_2__resource_not_entity01'),
    ]

    operations = [
        migrations.RunPython(set_resource_ids),
    ]
