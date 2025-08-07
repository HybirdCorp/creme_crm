import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0041_v2_7__number_generation03'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentinformation',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='paymentinformation',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
