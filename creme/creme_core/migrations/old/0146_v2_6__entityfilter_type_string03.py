from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0145_v2_6__entityfilter_type_string02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='entityfilter',
            name='old_filter_type',
        ),
    ]
