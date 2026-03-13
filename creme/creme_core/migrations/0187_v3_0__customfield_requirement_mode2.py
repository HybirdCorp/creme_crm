from django.db import migrations


def fill_requirement_mode(apps, schema_editor):
    apps.get_model('creme_core', 'CustomField').objects.filter(
        is_required=True,
    ).update(
        requirement_mode=2,  # REQUIRED
    )


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0186_v3_0__customfield_requirement_mode1'),
    ]

    operations = [
        migrations.RunPython(fill_requirement_mode),
    ]
