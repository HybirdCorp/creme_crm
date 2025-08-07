import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0163_v2_7__cremeuser_uuid02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cremeuser',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
