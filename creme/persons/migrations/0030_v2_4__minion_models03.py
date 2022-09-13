from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0029_v2_4__minion_models02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='civility',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='legalform',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='position',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='sector',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='staffsize',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
    ]
