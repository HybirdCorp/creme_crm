from django.db import migrations


def create_charts(apps, schema_editor):
    # TODO: manage swapped graph model?
    ReportChart = apps.get_model('reports', 'ReportChart')

    for rgraph in apps.get_model('reports', 'ReportGraph').objects.exclude(
        uuid__in=ReportChart.objects.values_list('uuid', flat=True),
    ):
        ReportChart.objects.create(
            created=rgraph.created,
            modified=rgraph.modified,
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

# TODO: bricks
#     - ('reports', 'graphs') => ('reports', 'report_charts')
#     - ('reports', 'graph') => ('reports', 'chart') INSTANCE
#     - ('reports', 'graph') => ('reports', 'chart') BASIC
# TODO: clean ContentType? in 2.9 ?
class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0016_v2_8__reportchart01'),
    ]

    operations = [
        migrations.RunPython(create_charts),
        # TODO: other conversion (bricks, ...)
    ]
