from django.db import migrations

from creme.creme_core.models.fields import ColorField

OPEN_PK       = 1
CLOSED_PK     = 2
INVALID_PK    = 3
DUPLICATED_PK = 4
WONTFIX_PK    = 5

BASE_COLORS = {
    OPEN_PK:       'f8f223',
    CLOSED_PK:     '1dd420',
    INVALID_PK:    'adadad',
    DUPLICATED_PK: 'ababab',
    WONTFIX_PK:    'a387ab',
}

def generate_colors(apps, schema_editor):
    for status in apps.get_model('tickets', 'Status').objects.all():
        status.color = BASE_COLORS.get(status.id) or (
            '1dd420' if status.is_closed else ColorField.random()
        )
        status.save()


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0013_v2_5__status_color01'),
    ]

    operations = [
        migrations.RunPython(generate_colors),
    ]
