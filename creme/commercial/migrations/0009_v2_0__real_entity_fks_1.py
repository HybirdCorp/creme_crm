# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='commercialapproach',
            old_name='entity_id',
            new_name='old_entity_id',
        ),
        migrations.AlterField(
            model_name='commercialapproach',
            name='entity_content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='commercialapproach',
            name='entity',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
    ]
