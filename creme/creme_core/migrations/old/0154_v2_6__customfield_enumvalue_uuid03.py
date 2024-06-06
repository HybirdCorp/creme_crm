import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0153_v2_6__customfield_enumvalue_uuid02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customfieldenumvalue',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
