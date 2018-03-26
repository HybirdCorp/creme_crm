# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL

from creme.creme_core.models import fields as creme_fields


class Migration(migrations.Migration):
    # replaces = [
    #     (b'opportunities', '0001_initial'),
    #     (b'opportunities', '0002_v1_7__reference_not_null_1'),
    #     (b'opportunities', '0003_v1_7__reference_not_null_2'),
    #     (b'opportunities', '0004_v1_7__description_not_null_1'),
    #     (b'opportunities', '0005_v1_7__description_not_null_2'),
    #     (b'opportunities', '0006_v1_7__salesphase_lost_1'),
    #     (b'opportunities', '0007_v1_7__salesphase_lost_2'),
    # ]

    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Origin',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Origin')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Origin of opportunity',
                'verbose_name_plural': 'Origins of opportunity',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SalesPhase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('order', creme_fields.BasicAutoField(verbose_name='Order', editable=False, blank=True)),
                ('won', models.BooleanField(default=False, verbose_name='Won')),
                ('lost', models.BooleanField(default=False, verbose_name='Lost')),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Sale phase',
                'verbose_name_plural': 'Sale phases',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Opportunity',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the opportunity')),
                ('reference', models.CharField(max_length=100, verbose_name='Reference', blank=True)),
                ('estimated_sales', models.PositiveIntegerField(null=True, verbose_name='Estimated sales', blank=True)),
                ('made_sales', models.PositiveIntegerField(null=True, verbose_name='Made sales', blank=True)),
                ('chance_to_win', models.PositiveIntegerField(null=True, verbose_name='% of chance to win', blank=True)),
                ('expected_closing_date', models.DateField(null=True, verbose_name='Expected closing date', blank=True)),
                ('closing_date', models.DateField(null=True, verbose_name='Actual closing date', blank=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('first_action_date', models.DateField(null=True, verbose_name='Date of the first action', blank=True)),
                ('currency', models.ForeignKey(on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('origin', models.ForeignKey(on_delete=SET_NULL, verbose_name='Origin', blank=True, to='opportunities.Origin', null=True)),
                ('sales_phase', models.ForeignKey(on_delete=PROTECT, verbose_name='Sales phase', to='opportunities.SalesPhase')),
            ],
            options={
                'swappable': 'OPPORTUNITIES_OPPORTUNITY_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Opportunity',
                'verbose_name_plural': 'Opportunities',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
