from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0137_v2_6__brick_config_uuid02'),
    ]

    operations = [
        # CustomBrickConfigItem ------------------------------------------------
        migrations.RemoveField(
            model_name='CustomBrickConfigItem',
            name='old_id',
        ),
        migrations.DeleteModel(name='OldCustomBrickConfigItem'),

        # RelationBrickItem & InstanceBrickConfigItem --------------------------
        migrations.AlterField(
            model_name='RelationBrickItem',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='InstanceBrickConfigItem',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
    ]
