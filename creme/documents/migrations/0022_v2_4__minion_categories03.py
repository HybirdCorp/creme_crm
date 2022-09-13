import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0021_v2_4__minion_categories02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='foldercategory',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
