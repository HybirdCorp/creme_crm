import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0161_v2_7__propertytype_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
