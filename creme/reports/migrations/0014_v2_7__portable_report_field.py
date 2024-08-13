from django.db import migrations

from creme.reports.constants import RFT_AGG_CUSTOM, RFT_CUSTOM


def customfields_id_to_uuid(apps, schema_editor):
    id_to_uuid = dict(
        apps.get_model('creme_core', 'CustomField').objects.values_list('id', 'uuid')
    )

    Field = apps.get_model('reports', 'Field')
    for rfield in Field.objects.filter(type=RFT_CUSTOM):
        rfield.name = id_to_uuid[int(rfield.name)]
        rfield.save()

    for rfield in Field.objects.filter(type=RFT_AGG_CUSTOM):
        cf_id, agg_id = rfield.name.split('__', 1)
        rfield.name = f'{id_to_uuid[int(cf_id)]}__{agg_id}'
        rfield.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(customfields_id_to_uuid),
    ]
