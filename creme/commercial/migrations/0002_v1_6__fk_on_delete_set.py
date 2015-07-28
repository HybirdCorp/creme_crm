# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('commercial', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='act',
            name='segment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Related segment', to='commercial.MarketSegment'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='strategy',
            name='evaluated_orgas',
            field=models.ManyToManyField(verbose_name='Evaluated organisation(s)', null=True, editable=False, to=settings.PERSONS_ORGANISATION_MODEL),
            preserve_default=True,
        ),
    ]
