from django.db import migrations

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='additionalinformation',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='additionalinformation',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='creditnotestatus',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='creditnotestatus',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='paymentterms',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='paymentterms',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='quotestatus',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='quotestatus',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='salesorderstatus',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='salesorderstatus',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='settlementterms',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='settlementterms',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
    ]
