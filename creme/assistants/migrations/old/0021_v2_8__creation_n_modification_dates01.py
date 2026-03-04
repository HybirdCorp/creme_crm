from django.db import migrations

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0020_v2_8__priority_created_n_modified02'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='alert',
            name='creation_date',
            field=core_fields.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='alert',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='memo',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='todo',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
    ]
