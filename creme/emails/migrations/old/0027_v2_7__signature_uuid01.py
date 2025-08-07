import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0026_v2_7__workflowemail'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailsignature',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
