import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0028_v2_7__signature_uuid02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailsignature',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
