# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0010_v2_0__real_entity_fks_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='commercialapproach',
            name='old_entity_id',
        ),
        migrations.AlterField(
            model_name='commercialapproach',
            name='entity_content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='commercialapproach',
            name='entity',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='commercial_approaches'),
            preserve_default=False,
        ),
    ]
