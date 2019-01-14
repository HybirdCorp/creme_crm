# -*- coding: utf-8 -*-

from django.db import migrations
from django.db.models import ForeignKey
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='address',
            old_name='object_id',
            new_name='old_object_id',
        ),
        migrations.AlterField(
            model_name='address',
            name='content_type',
            field=ForeignKey(editable=False, on_delete=CASCADE, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='address',
            name='object',
            field=ForeignKey(default=None, editable=False, null=True, on_delete=CASCADE, to='creme_core.CremeEntity'),
        ),
    ]
