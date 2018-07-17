# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0013_v2_0__lwmail_body_json02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lightweightemail',
            name='body',
        ),
        migrations.RenameField(
                model_name='lightweightemail',
                old_name='body_tmp',
                new_name='body',
        ),
    ]
