from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='category',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='category',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='subcategory',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='subcategory',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='subcategory',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
    ]
