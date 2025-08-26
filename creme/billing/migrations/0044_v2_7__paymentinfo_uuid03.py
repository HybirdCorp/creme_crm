import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0043_v2_7__paymentinfo_uuid02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentinformation',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
