from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0037_v2_7__templatebase_status_uuid02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='templatebase',
            name='status_id',
        ),
    ]
