import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0142_v2_6__userrole_extra_data_n_uuid02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userrole',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
