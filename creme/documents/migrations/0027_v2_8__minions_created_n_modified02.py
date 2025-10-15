from django.db import migrations
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0026_v2_8__minions_created_n_modified01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentcategory',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='documentcategory',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AlterField(
            model_name='foldercategory',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='foldercategory',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
    ]
