from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0009_v2_2__abscissa_fields_rework03'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportgraph',
            name='ordinate_type',
            field=models.CharField(verbose_name='Y axis (type)', editable=False, max_length=100, default='',
                                   choices=[('count', 'Count'), ('avg', 'Average'), ('max', 'Maximum'), ('min', 'Minimum'), ('sum', 'Sum')],
                                  ),
        ),
        migrations.AddField(
            model_name='reportgraph',
            name='ordinate_cell_key',
            field=models.CharField(verbose_name='Y axis (field)', editable=False, max_length=100, default=''),
        ),
    ]
