# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeoAddress',
            fields=[
                #('address', models.OneToOneField(primary_key=True, serialize=False, to='persons.Address', verbose_name='Address')),
                ('address', models.OneToOneField(primary_key=True, serialize=False, to=settings.PERSONS_ADDRESS_MODEL, verbose_name='Address')),
                ('latitude', models.FloatField(null=True, verbose_name='Latitude', blank=True)),
                ('longitude', models.FloatField(null=True, verbose_name='Longitude', blank=True)),
                ('draggable', models.BooleanField(default=True, verbose_name='Is this marker draggable in maps ?')),
                ('geocoded', models.BooleanField(default=False, verbose_name='Geocoded from address ?')),
                ('status', models.SmallIntegerField(default=0, verbose_name='Status', choices=[(0, 'Not localized'), (1, 'Manual location'), (2, 'Partially matching location'), (3, b'')])),
            ],
            options={
                'verbose_name': 'Address',
                'verbose_name_plural': 'Addresses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Town',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the town')),
                ('slug', models.SlugField(max_length=100, verbose_name='Slugified name of the town')),
                ('zipcode', models.CharField(max_length=100, null=True, verbose_name='Zip code', blank=True)),
                ('country', models.CharField(max_length=40, null=True, verbose_name='Country', blank=True)),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
            ],
            options={
                'verbose_name': 'Town',
                'verbose_name_plural': 'Towns',
            },
            bases=(models.Model,),
        ),
    ]
