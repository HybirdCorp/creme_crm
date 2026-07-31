from django.db import migrations, models
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0203_v3_0__workflow_created_modified_disabled2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workflow',
            name='enabled',
        ),
        migrations.AlterField(
            model_name='workflow',
            name='created',
            field=core_fields.CreationDateTimeField(
                verbose_name='Creation date',
                blank=True, default=now, editable=False,
            ),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                verbose_name='Last modification',
                blank=True, default=now, editable=False,
            ),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='disabling_reason',
            field=models.TextField(editable=False),
        ),
    ]
