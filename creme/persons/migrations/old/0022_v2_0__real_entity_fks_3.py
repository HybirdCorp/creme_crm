# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0021_v2_0__real_entity_fks_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='address',
            name='old_object_id',
        ),
        migrations.AlterField(
            model_name='address',
            name='content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='address',
            name='object',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='persons_addresses'),
            preserve_default=False,
        ),
    ]
