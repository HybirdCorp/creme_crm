from django.db import migrations
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0021_v2_8__creation_n_modification_dates01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='alert',
            name='creation_date',
            field=core_fields.CreationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='alert',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='memo',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='todo',
            name='modification_date',
            field=core_fields.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
    ]
