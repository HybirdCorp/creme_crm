# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('assistants', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='action',
            old_name='entity_id',
            new_name='old_entity_id',
        ),
        migrations.RenameField(
            model_name='alert',
            old_name='entity_id',
            new_name='old_entity_id',
        ),
        migrations.RenameField(
            model_name='memo',
            old_name='entity_id',
            new_name='old_entity_id',
        ),
        migrations.RenameField(
            model_name='todo',
            old_name='entity_id',
            new_name='old_entity_id',
        ),
        migrations.RenameField(
            model_name='usermessage',
            old_name='entity_id',
            new_name='old_entity_id',
        ),

        # ----
        migrations.AlterField(
            model_name='action',
            name='entity_content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='alert',
            name='entity_content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='memo',
            name='entity_content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='todo',
            name='entity_content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='usermessage',
            name='entity_content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType', null=True),
        ),

        # ----
        migrations.AddField(
            model_name='action',
            name='entity',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
        migrations.AddField(
            model_name='alert',
            name='entity',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
        migrations.AddField(
            model_name='memo',
            name='entity',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
        migrations.AddField(
            model_name='todo',
            name='entity',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
        migrations.AddField(
            model_name='usermessage',
            name='entity',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
    ]
