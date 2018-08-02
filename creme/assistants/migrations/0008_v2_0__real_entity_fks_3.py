# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0007_v2_0__real_entity_fks_2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='action',
            name='old_entity_id',
        ),
        migrations.RemoveField(
            model_name='alert',
            name='old_entity_id',
        ),
        migrations.RemoveField(
            model_name='memo',
            name='old_entity_id',
        ),
        migrations.RemoveField(
            model_name='todo',
            name='old_entity_id',
        ),
        migrations.RemoveField(
            model_name='usermessage',
            name='old_entity_id',
        ),

        # ---
        migrations.AlterField(
            model_name='action',
            name='entity_content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='alert',
            name='entity_content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='memo',
            name='entity_content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='todo',
            name='entity_content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='usermessage',
            name='entity_content_type',
            field=EntityCTypeForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType', null=True),
        ),

        # ---
        migrations.AlterField(
            model_name='action',
            name='entity',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='assistants_actions'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='alert',
            name='entity',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='assistants_alerts'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='memo',
            name='entity',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='assistants_memos'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='todo',
            name='entity',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', related_name='assistants_todos'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='usermessage',
            name='entity',
            field=ForeignKey(default=None, editable=False, on_delete=CASCADE, to='creme_core.CremeEntity', null=True, related_name='assistants_messages'),
            preserve_default=False,
        ),
    ]
