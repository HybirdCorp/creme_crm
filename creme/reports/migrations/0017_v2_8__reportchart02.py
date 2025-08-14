from django.db import migrations


def create_charts(apps, schema_editor):
    # TODO: manage swapped graph model?
    ReportChart = apps.get_model('reports', 'ReportChart')

    for rgraph in apps.get_model('reports', 'ReportGraph').objects.exclude(
        uuid__in=ReportChart.objects.values_list('uuid', flat=True),
    ):
        ReportChart.objects.create(
            user=rgraph.user,
            created=rgraph.created,
            modified=rgraph.modified,  # Hum now() seems used anyway...
            uuid=rgraph.uuid,
            name=rgraph.name,
            linked_report_id=rgraph.linked_report_id,
            description=rgraph.description,

            abscissa_type=rgraph.abscissa_type,
            abscissa_cell_value=rgraph.abscissa_cell_value,
            abscissa_parameter=rgraph.abscissa_parameter,

            ordinate_type=rgraph.ordinate_type,
            ordinate_cell_key=rgraph.ordinate_cell_key,

            plot_name=rgraph.chart,
            asc=rgraph.asc,

            extra_data=rgraph.extra_data,
        )

def convert_bricks(apps, schema_editor):
    apps.get_model('creme_core', 'BrickDetailviewLocation').objects.filter(
        brick_id='regular-reports-graphs',
    ).update(brick_id='regular-reports-report_charts')

    ReportGraph = apps.get_model('reports', 'ReportGraph')
    for ibci in apps.get_model('creme_core', 'InstanceBrickConfigItem').objects.filter(
        brick_class_id='instance-reports-graph',
    ):
        rgraph = ReportGraph.objects.get(id=ibci.entity_id)

        extra_data = ibci.json_extra_data
        # NB: a ReportChart & its related ReportGraph have the same UUID
        #     (see create_charts())
        extra_data['chart'] = str(rgraph.uuid)

        ibci.brick_class_id = 'instance-reports-chart'
        ibci.entity_id = rgraph.linked_report_id
        ibci.json_extra_data = extra_data
        ibci.save()


def delete_graphes(apps, schema_editor):
    # NB: if we do not delete them explicitly, the CremeEntity part is not
    #     removed when the table is deleted (0018_v2_8__reportchart03.py)
    apps.get_model('reports', 'ReportGraph').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0016_v2_8__reportchart01'),
    ]

    operations = [
        migrations.RunPython(create_charts),
        migrations.RunPython(convert_bricks),
        migrations.RunPython(delete_graphes),
        # TODO: remove the ContentType for ReportGraph in next version
    ]
