import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0114_v2_4__unique_user_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='currency',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='language',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='language',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='language',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='vat',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='vat',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),  # unique=True
        ),
    ]
