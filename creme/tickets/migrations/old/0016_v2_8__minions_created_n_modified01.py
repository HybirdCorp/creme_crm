from django.db import migrations

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='criticity',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='criticity',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='priority',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='priority',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='status',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='status',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
    ]
