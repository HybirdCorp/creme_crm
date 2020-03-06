from django.db import migrations

CLOSED_PK = 2


def set_closed_field(apps, schema_editor):
    apps.get_model('tickets', 'Status').objects.filter(id=CLOSED_PK).update(is_closed=True)


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0008_v2_2__status_is_closed01'),
    ]

    operations = [
        migrations.RunPython(set_closed_field),
    ]
