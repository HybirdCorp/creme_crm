from django.db import migrations

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0035_v2_8__minions_created_n_modified02'),
    ]

    operations = [
        migrations.AddField(
            model_name='calendar',
            name='created',
            field=core_fields.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='calendar',
            name='modified',
            field=core_fields.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
    ]
