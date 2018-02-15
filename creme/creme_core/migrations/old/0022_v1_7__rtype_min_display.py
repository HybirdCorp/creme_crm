# -*- coding: utf-8 -*-

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0021_v1_7__old_prop_managed_custom'),
    ]

    operations = [
        migrations.AddField(
            model_name='relationtype',
            name='minimal_display',
            field=models.BooleanField(default=False),
        ),
    ]
