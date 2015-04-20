# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('media_managers', '0001_initial'),
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the category')),
                ('description', models.CharField(max_length=100, verbose_name='Description')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the sub-category')),
                ('description', models.CharField(max_length=100, verbose_name='Description')),
                ('category', models.ForeignKey(verbose_name='Parent category', to='products.Category')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Sub-category',
                'verbose_name_plural': 'Sub-categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('code', models.IntegerField(default=0, verbose_name='Code')),
                ('description', models.CharField(max_length=200, verbose_name='Description')),
                ('unit_price', models.DecimalField(verbose_name='Unit price', max_digits=8, decimal_places=2)),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                ('quantity_per_unit', models.IntegerField(null=True, verbose_name='Quantity/Unit', blank=True)),
                ('weight', models.DecimalField(null=True, verbose_name='Weight', max_digits=8, decimal_places=2, blank=True)),
                ('stock', models.IntegerField(null=True, verbose_name='Quantity/Stock', blank=True)),
                ('web_site', models.CharField(max_length=100, null=True, verbose_name='Web Site', blank=True)),
                ('category', models.ForeignKey(verbose_name='Category', to='products.Category')),
                ('sub_category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Sub-category', to='products.SubCategory')),
                ('images', models.ManyToManyField(related_name='ProductImages_set', null=True, verbose_name='Images', to='media_managers.Image', blank=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Product',
                'verbose_name_plural': 'Products',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('description', models.CharField(max_length=200, verbose_name='Description')),
                ('reference', models.CharField(max_length=100, verbose_name='Reference')),
                ('countable', models.BooleanField(default=False, verbose_name='Countable')),
                ('unit', models.CharField(max_length=100, verbose_name='Unit', blank=True)),
                ('quantity_per_unit', models.IntegerField(null=True, verbose_name='Quantity/Unit', blank=True)),
                ('unit_price', models.DecimalField(verbose_name='Unit price', max_digits=8, decimal_places=2)),
                ('web_site', models.CharField(max_length=100, null=True, verbose_name='Web Site', blank=True)),
                ('category', models.ForeignKey(verbose_name='Category', to='products.Category')),
                ('sub_category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, verbose_name='Sub-category', to='products.SubCategory')),
                ('images', models.ManyToManyField(related_name='ServiceImages_set', null=True, verbose_name='Images', to='media_managers.Image', blank=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Service',
                'verbose_name_plural': 'Services',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
