from uuid import uuid4

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0026_v2_4__minion_models02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='additionalinformation',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='creditnotestatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='invoicestatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='paymentterms',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='quotestatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='salesorderstatus',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='settlementterms',
            name='uuid',
            field=models.UUIDField(default=uuid4, editable=False, unique=True),
        ),
    ]
