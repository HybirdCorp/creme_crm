from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reportgraph',
            old_name='type',
            new_name='abscissa_type',
        ),
        migrations.RenameField(
            model_name='reportgraph',
            old_name='abscissa',
            new_name='abscissa_cell_value',
        ),
        migrations.AddField(
            model_name='reportgraph',
            name='abscissa_parameter',
            field=models.TextField(verbose_name='X axis parameter', editable=False, null=True),
        ),
    ]
