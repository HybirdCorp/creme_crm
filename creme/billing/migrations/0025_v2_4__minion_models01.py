from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0024_v2_4__delete_cloned_addresses'),
    ]

    operations = [
        migrations.AddField(
            model_name='additionalinformation',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='additionalinformation',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='creditnotestatus',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='creditnotestatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='paymentterms',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='paymentterms',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='quotestatus',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='quotestatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='salesorderstatus',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='salesorderstatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
        migrations.AddField(
            model_name='settlementterms',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='settlementterms',
            name='is_custom',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='settlementterms',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False),  # unique=True
        ),
    ]
