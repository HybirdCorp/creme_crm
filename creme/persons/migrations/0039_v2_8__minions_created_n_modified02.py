from django.db import migrations
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0038_v2_8__minions_created_n_modified01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='civility',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='civility',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AlterField(
            model_name='legalform',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='legalform',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AlterField(
            model_name='position',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='position',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AlterField(
            model_name='sector',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='sector',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AlterField(
            model_name='staffsize',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AlterField(
            model_name='staffsize',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=now, editable=False, verbose_name='Last modification',
            ),
        ),
    ]
