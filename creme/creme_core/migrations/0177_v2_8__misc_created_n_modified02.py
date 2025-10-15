from django.db import migrations
from django.utils.timezone import now

import creme.creme_core.models.fields as core_field


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0176_v2_8__misc_created_n_modified01'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cremeproperty',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='cremeuser',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='entityfilter',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='entityfilter',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='headerfilter',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='headerfilter',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='userrole',
            name='created',
            field=core_field.CreationDateTimeField(blank=True, default=now, editable=False),
        ),
        migrations.AlterField(
            model_name='userrole',
            name='modified',
            field=core_field.ModificationDateTimeField(blank=True, default=now, editable=False),
        ),
    ]
