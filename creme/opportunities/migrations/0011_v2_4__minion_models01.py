from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='origin',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='origin',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='origin',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='salesphase',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='salesphase',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='salesphase',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
    ]
