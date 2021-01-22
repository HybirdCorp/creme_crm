from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0011_v2_2__ordinate_field_rework02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportgraph',
            name='ordinate',
        ),
        migrations.RemoveField(
            model_name='reportgraph',
            name='is_count',
        ),
    ]
