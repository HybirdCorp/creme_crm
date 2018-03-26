# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models import fields as creme_fields


class Migration(migrations.Migration):
    # replaces = [
    #     (b'recurrents', '0001_initial'),
    #     (b'recurrents', '0002_v1_7__name_not_null_1'),
    #     (b'recurrents', '0003_v1_7__name_not_null_2'),
    #     (b'recurrents', '0004_v1_7__description_not_null_1'),
    #     (b'recurrents', '0005_v1_7__description_not_null_2'),
    # ]

    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurrentGenerator',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the generator', blank=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('first_generation', models.DateTimeField(verbose_name='Date of the first generation')),
                ('last_generation', models.DateTimeField(verbose_name='Date of the last generation', null=True, editable=False)),
                ('periodicity', creme_fields.DatePeriodField(verbose_name='Periodicity of the generation')),
                ('is_working', models.BooleanField(default=True, verbose_name='Active ?', editable=False)),
                ('ct', creme_fields.CTypeForeignKey(editable=False, to='contenttypes.ContentType', verbose_name='Type of the recurrent resource')),
                ('template', models.ForeignKey(to='creme_core.CremeEntity', on_delete=CASCADE,
                                               related_name='template_set', editable=False,
                                               verbose_name='Related model'
                                              )
                ),
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
