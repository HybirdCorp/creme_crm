# -*- coding: utf-8 -*-

from django.db import migrations


def clean_db(apps, schema_editor):
    get_model = apps.get_model

    ct_resource = get_model('contenttypes', 'ContentType').objects.filter(
        app_label='projects', model='resource',
    ).first()
    if ct_resource is None:
        return

    ct_id = ct_resource.id
    get_model('creme_core', 'HeaderFilter').objects.filter(entity_type_id=ct_id).delete()
    get_model('creme_core', 'SearchConfigItem').objects.filter(content_type_id=ct_id).delete()
    get_model('creme_core', 'CremeEntity').objects.filter(entity_type_id=ct_id).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0022_v2_2__resource_not_entity03'),
    ]

    operations = [
        migrations.RunPython(clean_db),
    ]
