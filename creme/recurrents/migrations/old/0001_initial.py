# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurrentGenerator',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, null=True, verbose_name='Name of the generator', blank=True)),
                ('description', models.TextField(null=True, verbose_name='Description', blank=True)),
                ('first_generation', models.DateTimeField(verbose_name='Date of the first generation')),
                ('last_generation', models.DateTimeField(verbose_name='Date of the last generation', null=True, editable=False)),
                ('periodicity', creme.creme_core.models.fields.DatePeriodField(verbose_name='Periodicity of the generation')),
                ('is_working', models.BooleanField(default=True, verbose_name='Active ?', editable=False)),
                ('ct', creme.creme_core.models.fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType', verbose_name='Type of the recurrent resource')),
                ('template', models.ForeignKey(related_name='template_set', editable=False, to='creme_core.CremeEntity', verbose_name='Related model')),
            ],
            options={
                'swappable': 'RECURRENTS_RGENERATOR_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Recurrent generator',
                'verbose_name_plural': 'Recurrent generators',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
