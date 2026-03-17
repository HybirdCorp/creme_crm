from django.db import migrations


def remove_28_migration_data(apps, schema_editor):
    for role in apps.get_model('creme_core', 'UserRole').objects.filter(
        extra_data__listablemigr=True,
    ):
        extra_data = role.extra_data
        del extra_data['listablemigr']
        role.extra_data = extra_data
        role.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_28_migration_data),
    ]
