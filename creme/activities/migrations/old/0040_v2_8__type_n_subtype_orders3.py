from django.db import migrations, models

from creme.creme_core.models.fields import BasicAutoField


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0039_v2_8__type_n_subtype_orders2'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='activitytype',
            options={
                'ordering': ('order',),
                'verbose_name': 'Type of activity',
                'verbose_name_plural': 'Types of activity',
            },
        ),
        migrations.AlterModelOptions(
            name='activitysubtype',
            options={
                'ordering': ('order',),
                'verbose_name': 'Sub-type of activity',
                'verbose_name_plural': 'Sub-types of activity',
            },
        ),

        migrations.AlterField(
            model_name='activitytype',
            name='order',
            field=BasicAutoField(blank=True, editable=False),
        ),
        migrations.AlterField(
            model_name='activitysubtype',
            name='order',
            field=models.PositiveIntegerField(default=None, editable=False),
        ),
    ]
