# -*- coding: utf-8 -*-

from django.db import migrations, models
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import CTypeOneToOneField


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0053_v2_1__setcredentials_forbidden'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeletionCommand',
            fields=[
                ('content_type', CTypeOneToOneField(editable=False, on_delete=CASCADE, primary_key=True, serialize=False, to='contenttypes.ContentType')),
                ('job', models.ForeignKey(on_delete=CASCADE, to='creme_core.Job', editable=False)),
                ('pk_to_delete', models.TextField(editable=False)),
                ('deleted_repr', models.TextField(editable=False)),
                ('json_replacers', models.TextField(default='[]', editable=False)),
                ('total_count', models.PositiveIntegerField(default=0, editable=False)),
                ('updated_count', models.PositiveIntegerField(default=0, editable=False)),
            ],
        ),
    ]
