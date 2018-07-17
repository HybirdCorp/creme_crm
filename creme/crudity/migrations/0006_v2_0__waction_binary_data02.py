# -*- coding: utf-8 -*-
from django.db import migrations


def copy_data(apps, schema_editor):
    for waction in apps.get_model('crudity', 'WaitingAction').objects.exclude(raw_data=None):
        waction.raw_data_tmp = waction.raw_data.encode()
        waction.save()


class Migration(migrations.Migration):
    dependencies = [
        ('crudity', '0005_v2_0__waction_binary_data01'),
    ]

    operations = [
        migrations.RunPython(copy_data),
    ]
