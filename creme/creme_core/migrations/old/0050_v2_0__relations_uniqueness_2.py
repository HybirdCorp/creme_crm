# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0049_v2_0__relations_uniqueness_1'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='relation',
            unique_together={('type', 'subject_entity', 'object_entity')},
        ),
    ]
