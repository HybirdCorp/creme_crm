from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0011_v2_4__minion_models02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='criticity',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='priority',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='status',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
    ]
