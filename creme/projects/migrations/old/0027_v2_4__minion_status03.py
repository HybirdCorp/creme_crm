from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0026_v2_4__minion_status02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectstatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='taskstatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
    ]
