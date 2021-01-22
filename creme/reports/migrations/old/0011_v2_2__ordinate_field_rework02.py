from django.conf import settings
from django.db import migrations


def convert_ordinate(apps, schema_editor):
    if settings.REPORTS_GRAPH_MODEL == 'reports.ReportGraph':
        for rgraph in apps.get_model('reports', 'ReportGraph').objects.all():
            if rgraph.is_count:
                rgraph.ordinate_type = 'count'
            else:
                cell_value, agg_type = rgraph.ordinate.split('__', 1)
                rgraph.ordinate_type = agg_type
                rgraph.ordinate_cell_key = f'custom_field-{cell_value}' \
                                           if cell_value.isdigit() else \
                                           f'regular_field-{cell_value}'

            rgraph.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0010_v2_2__ordinate_field_rework01'),
    ]

    operations = [
        migrations.RunPython(convert_ordinate),
    ]
