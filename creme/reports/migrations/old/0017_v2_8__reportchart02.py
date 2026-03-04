from json import loads as json_load

from django.db import migrations

from creme.creme_core.models.history import _JSONEncoder as JSONEncoder


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

            extra_data={
                'old_graph_id': rgraph.id,
                **rgraph.extra_data,
            },
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


def convert_history(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    report_ctype = ContentType.objects.filter(app_label='reports', model='report').first()
    if report_ctype is None:
        return

    graph_ctype = ContentType.objects.filter(app_label='reports', model='reportgraph').first()
    if graph_ctype is None:
        return

    chart_ctype = ContentType.objects.get_or_create(app_label='reports', model='reportchart')[0]

    HistoryLine = apps.get_model('creme_core', 'HistoryLine')
    ReportChart = apps.get_model('reports', 'ReportChart')

    encode = JSONEncoder().encode
    # ---
    TYPE_AUX_CREATION = 10
    for hline in HistoryLine.objects.filter(
        entity_ctype_id=report_ctype.id, type=TYPE_AUX_CREATION,
    ):
        # Value == [report_as_str, graph_ctype_id, graph_id, graph_as_str]
        decoded_value = json_load(hline.value)
        if decoded_value[1] == graph_ctype.id:
            chart = ReportChart.objects.filter(extra_data__old_graph_id=decoded_value[2]).first()
            hline.value = encode([
                decoded_value[0],
                chart_ctype.id,
                0 if chart is None else chart.id,
                decoded_value[3],
            ])

            hline.save()

    # ---
    TYPE_AUX_EDITION  = 11
    for hline in HistoryLine.objects.filter(
        entity_ctype_id=report_ctype.id, type=TYPE_AUX_EDITION,
    ):
        # Value == [
        #     report_as_str,
        #     [graph_ctype_id, graph_id, graph_as_str],
        #     [field_name1, ...],
        #     [field_name2, ...],
        #     ...,
        # ]
        decoded_value = json_load(hline.value)
        if decoded_value[1][0] == graph_ctype.id:
            chart = ReportChart.objects.filter(extra_data__old_graph_id=decoded_value[1][1]).first()
            hline.value = encode([
                decoded_value[0],
                [
                    chart_ctype.id,
                    0 if chart is None else chart.id,
                    decoded_value[1][2],
                ],
                *decoded_value[2:],  # TODO: convert/delete fields ("chart" => "plot_name")?
            ])

            hline.save()

    # ---
    TYPE_AUX_DELETION = 12
    for hline in HistoryLine.objects.filter(
        entity_ctype_id=report_ctype.id, type=TYPE_AUX_DELETION,
    ):
        # Value == [report_as_str, graph_ctype_id, graph_as_str]
        decoded_value = json_load(hline.value)
        if decoded_value[1] == graph_ctype.id:
            hline.value = encode([
                decoded_value[0], chart_ctype.id, decoded_value[2],
            ])
            hline.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0016_v2_8__reportchart01'),
    ]

    operations = [
        migrations.RunPython(create_charts),
        migrations.RunPython(convert_bricks),
        migrations.RunPython(convert_history),
    ]
