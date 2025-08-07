from django.db import migrations


def fill_uuids(apps, schema_editor):
    for tpl in apps.get_model('billing', 'TemplateBase').objects.all():
        tpl.status_uuid = apps.get_model(
            'billing', f'{tpl.ct.model}status'  # e.g. Invoice => InvoiceStatus
        ).objects.get(id=tpl.status_id).uuid
        tpl.save()



class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0036_v2_7__templatebase_status_uuid01'),
    ]

    operations = [
        migrations.RunPython(fill_uuids),
    ]
