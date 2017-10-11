# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('commercial', '0002_v1_6__fk_on_delete_set'),
    ]

    operations = [
        migrations.AlterField(
            model_name='strategy',
            name='evaluated_orgas',
            field=models.ManyToManyField(verbose_name='Evaluated organisation(s)', editable=False, to=settings.PERSONS_ORGANISATION_MODEL),
        ),
    ]
