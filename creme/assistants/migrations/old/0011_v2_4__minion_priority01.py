import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0010_v2_4__nullable_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='usermessagepriority',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='usermessagepriority',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),  # unique=True
        ),
    ]
