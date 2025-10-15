from django.db import migrations
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0040_v2_8__address_created_n_modified01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='created',
            field=core_fields.CreationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='address',
            name='modified',
            field=core_fields.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
    ]
