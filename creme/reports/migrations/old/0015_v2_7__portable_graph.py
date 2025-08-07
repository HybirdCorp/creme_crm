from django.db import migrations

from creme.reports.constants import AbscissaGroup


def customfields_id_to_uuid(apps, schema_editor):
    id_to_uuid = dict(
        apps.get_model('creme_core', 'CustomField').objects.values_list('id', 'uuid')
    )

    ReportGraph = apps.get_model('reports', 'ReportGraph')
    for rgraph in ReportGraph.objects.filter(
        abscissa_type__in=[
            AbscissaGroup.CUSTOM_DAY,
            AbscissaGroup.CUSTOM_MONTH,
            AbscissaGroup.CUSTOM_YEAR,
            AbscissaGroup.CUSTOM_RANGE,
            AbscissaGroup.CUSTOM_FK,
        ],
    ):
        rgraph.abscissa_cell_value = id_to_uuid[int(rgraph.abscissa_cell_value)]
        rgraph.save()

    for rgraph in ReportGraph.objects.filter(ordinate_cell_key__startswith='custom_field-'):
        prefix, cf_id = rgraph.ordinate_cell_key.split('-', 1)
        rgraph.ordinate_cell_key = f'{prefix}-{id_to_uuid[int(cf_id)]}'
        rgraph.save()


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('reports', '0014_v2_7__portable_report_field'),
    ]

    operations = [
        migrations.RunPython(customfields_id_to_uuid),
    ]
