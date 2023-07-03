from django.db import migrations

from creme.creme_core.models.fields import ColorField


def generate_colors(apps, schema_editor):
    for status in apps.get_model('activities', 'Status').objects.all():
        status.color = ColorField.random()
        status.save()


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0020_v2_5__status_color01'),
    ]

    operations = [
        migrations.RunPython(generate_colors),
    ]
