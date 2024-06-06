import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0151_v2_6__filters_extra_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfieldenumvalue',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
