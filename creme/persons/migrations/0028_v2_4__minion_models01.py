from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0002_v2_4__unique_user_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='civility',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='civility',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='civility',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='legalform',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='legalform',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='legalform',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='position',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='position',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='position',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='sector',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='sector',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='sector',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='staffsize',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='staffsize',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='staffsize',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
    ]
