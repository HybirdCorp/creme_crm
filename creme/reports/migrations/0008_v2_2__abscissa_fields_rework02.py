from django.conf import settings
from django.db import migrations


def convert_days(apps, schema_editor):
    if settings.REPORTS_GRAPH_MODEL == 'reports.ReportGraph':
        for rgraph in apps.get_model('reports', 'ReportGraph').objects.exclude(days__isnull=True):
            rgraph.abscissa_parameter = str(rgraph.days)
            rgraph.save()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0007_v2_2__abscissa_fields_rework01'),
    ]

    operations = [
        migrations.RunPython(convert_days),
    ]
