from django.db import migrations

import creme.creme_core.models.fields as core_field

from .utils.utils_27 import EPOCH


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0175_v2_8__minions_created_n_modified02'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeproperty',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='cremeuser',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='entityfilter',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='entityfilter',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='headerfilter',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='headerfilter',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='userrole',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
        migrations.AddField(
            model_name='userrole',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=EPOCH, editable=False),
        ),
    ]
