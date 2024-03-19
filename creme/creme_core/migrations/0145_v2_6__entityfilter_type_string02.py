from django.db import migrations


def fix_filter_types(apps, schema_editor):
    # EF_CREDENTIALS
    apps.get_model(
        'creme_core', 'EntityFilter'
    ).objects.filter(old_filter_type=0).update(filter_type='creme_core-credentials')


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0144_v2_6__entityfilter_type_string01'),
    ]

    operations = [
        migrations.RunPython(fix_filter_types),
    ]
