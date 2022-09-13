import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='acttype',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='acttype',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),  # unique=True
        ),
    ]
