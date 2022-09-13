import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0014_v2_4__minion_type02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='acttype',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
