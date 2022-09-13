import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0012_v2_4__minion_priority02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usermessagepriority',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
