# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0011_v2_0__real_entity_fks_3'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='commercialapproach',
            name='ok_or_in_futur',
        ),
    ]
