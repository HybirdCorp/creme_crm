from django.db import migrations


def fix_button_ids(apps, schema_editor):
    prefix = 'button_'
    length = len(prefix)

    for instance in apps.get_model('creme_core', 'ButtonMenuItem').objects.filter(
        button_id__startswith=prefix,
    ):
        instance.button_id = instance.button_id[length:]
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0146_v2_6__entityfilter_type_string03'),
    ]

    operations = [
        migrations.RunPython(fix_button_ids),
    ]
