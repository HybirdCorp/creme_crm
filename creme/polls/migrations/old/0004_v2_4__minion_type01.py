import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('polls', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='polltype',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='polltype',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='polltype',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),  # unique=True
        ),
    ]
