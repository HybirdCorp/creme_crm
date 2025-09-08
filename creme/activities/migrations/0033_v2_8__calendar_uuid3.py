import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0032_v2_8__calendar_uuid2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calendar',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
