from django.db import migrations, models

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_30 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0201_v3_0__instancebrickconfigitem_real_entity_fk3'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='created',
            field=core_fields.CreationDateTimeField(
                verbose_name='Creation date',
                blank=True, default=EPOCH, editable=False,
            ),
        ),
        migrations.AddField(
            model_name='workflow',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                verbose_name='Last modification',
                blank=True, default=EPOCH, editable=False,
            ),
        ),
        migrations.AddField(
            model_name='workflow',
            name='disabled',
            field=models.DateTimeField(editable=False, null=True, verbose_name='Disabled'),
        ),
        migrations.AddField(
            model_name='workflow',
            name='disabling_reason',
            field=models.TextField(default='', editable=False),
        ),
    ]
