from django.db import migrations

import creme.creme_core.models.fields as core_fields
from creme.creme_core.migrations.utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='civility',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='civility',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='legalform',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='legalform',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='position',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='position',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='sector',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='sector',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
        migrations.AddField(
            model_name='staffsize',
            name='created',
            field=core_fields.CreationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Creation date',
            ),
        ),
        migrations.AddField(
            model_name='staffsize',
            name='modified',
            field=core_fields.ModificationDateTimeField(
                blank=True, default=EPOCH, editable=False, verbose_name='Last modification',
            ),
        ),
    ]
