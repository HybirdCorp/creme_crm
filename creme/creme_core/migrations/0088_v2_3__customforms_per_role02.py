from django.db import migrations


def create_new_instances(apps, schema_editor):
    get_model = apps.get_model
    create = get_model('creme_core', 'CustomFormConfigItem').objects.create

    for old_cfci in get_model('creme_core', 'OldCustomFormConfigItem').objects.all():
        create(
            descriptor_id=old_cfci.cform_id,
            json_groups=old_cfci.json_groups,
            role=None,
            superuser=False,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0087_v2_3__customforms_per_role01'),
    ]

    operations = [
        migrations.RunPython(create_new_instances),
    ]
