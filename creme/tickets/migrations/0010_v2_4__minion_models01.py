from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='criticity',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='criticity',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='criticity',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='priority',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='priority',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='priority',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='status',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='status',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
    ]
