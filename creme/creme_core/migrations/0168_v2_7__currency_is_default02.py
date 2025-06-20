from django.db import migrations


def fix_default(apps, schema_editor):
    first = apps.get_model('creme_core', 'Currency').objects.order_by('id').first()
    if first is not None:
        first.is_default = True
        first.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0167_v2_7__currency_is_default01'),
    ]

    operations = [
        migrations.RunPython(fix_default),
    ]
