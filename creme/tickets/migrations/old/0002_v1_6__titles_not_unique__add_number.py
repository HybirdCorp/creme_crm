# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TicketNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.AddField(
            model_name='ticket',
            name='number',
            field=models.PositiveIntegerField(default=1, verbose_name='Number', editable=False),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='title',
            field=models.CharField(max_length=100, verbose_name='Title', blank=True),
        ),
        migrations.AlterField(
            model_name='tickettemplate',
            name='title',
            field=models.CharField(max_length=100, verbose_name='Title', blank=True),
        ),
    ]
