import uuid

from django.conf import settings
from django.db import migrations, models
from django.utils.timezone import now

from creme.creme_core.models import fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportChart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'user',
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL, default=None, editable=False, null=True, on_delete=models.SET_NULL,
                    )
                ),
                ('created', core_fields.CreationDateTimeField(default=now, editable=False, blank=True)),
                ('modified', core_fields.ModificationDateTimeField(default=now, editable=False, blank=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the chart')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                (
                    'abscissa_type',
                    models.PositiveIntegerField(
                        editable=False, verbose_name='X axis (grouping)',
                        choices=[
                            (1, 'By days'),
                            (2, 'By months'),
                            (3, 'By years'),
                            (4, 'By X days'),
                            (5, 'By values (configurable)'),
                            (6, 'By values (of related entities)'),
                            (7, 'By values (not configurable)'),
                            (11, 'By days (custom field)'),
                            (12, 'By months (custom field)'),
                            (13, 'By years (custom field)'),
                            (14, 'By X days (custom field)'),
                            (15, 'By values (of custom choices)'),
                        ],
                    )
                ),
                (
                    'abscissa_cell_value',
                    models.CharField(editable=False, max_length=100, verbose_name='X axis (field)')
                ),
                (
                    'abscissa_parameter',
                    models.TextField(editable=False, null=True, verbose_name='X axis parameter')
                ),
                (
                    'ordinate_type',
                    models.CharField(
                        verbose_name='Y axis (type)',
                        choices=[
                            ('count', 'Count'), ('avg', 'Average'),
                            ('max', 'Maximum'), ('min', 'Minimum'), ('sum', 'Sum'),
                        ],
                        default='', editable=False, max_length=100,
                    )
                ),
                (
                    'ordinate_cell_key',
                    models.CharField(default='', editable=False, max_length=100, verbose_name='Y axis (field)')
                ),
                ('plot_name', models.CharField(max_length=100, null=True, verbose_name='Plot type')),
                ('asc', models.BooleanField(default=True, editable=False, verbose_name='ASC order')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                (
                    'linked_report',
                    models.ForeignKey(
                        to=settings.REPORTS_REPORT_MODEL,
                        editable=False, related_name='charts',
                        on_delete=models.CASCADE,
                    )
                ),
            ],
            options={
                'verbose_name': 'Report chart',
                'verbose_name_plural': 'Report charts',
                'ordering': ['name'],
            },
        ),
    ]
