import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0016_v2_4__minion_models02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='status',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
