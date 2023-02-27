from django.db import migrations

from creme.creme_core.models.fields import ColorField


def generate_colors(apps, schema_editor):
    for phase in apps.get_model('opportunities', 'SalesPhase').objects.all():
        phase.color = (
            '1dd420' if phase.won else
            'ae4444' if phase.lost else
            ColorField.random()
        )
        phase.save()


class Migration(migrations.Migration):
    dependencies = [
        ('opportunities', '0015_v2_5__salesphase_color01'),
    ]

    operations = [
        migrations.RunPython(generate_colors),
    ]
