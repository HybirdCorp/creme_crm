from django.db import migrations


def fix_dyn_alerts(apps, schema_editor):
    for alert in apps.get_model('assistants', 'Alert').objects.filter(
        trigger_offset__has_key='cell',
        is_validated=False,
    ):
        if alert.trigger_offset['cell']['value'] == 'modified':
            print(
                f'BEWARE: the Alert "{alert.title}" (id={alert.id}) used a '
                f'dynamic trigger on the field "modified", which is now '
                f'forbidden. The trigger date has been converted to be static.'
            )

            alert.trigger_offset = {}
            alert.save()


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_dyn_alerts),
    ]
