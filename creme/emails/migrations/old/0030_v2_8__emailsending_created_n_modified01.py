from django.db import migrations

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailsending',
            name='created',
            field=core_fields.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='emailsending',
            name='modified',
            field=core_fields.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
    ]
