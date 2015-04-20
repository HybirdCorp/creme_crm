# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Graph',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='creme_core.CremeEntity')),
                ('name', models.CharField(max_length=100, verbose_name='Name of the graph')),
                ('orbital_relation_types', models.ManyToManyField(to='creme_core.RelationType', verbose_name='Types of the peripheral relations')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Graph',
                'verbose_name_plural': 'Graphs',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='RootNode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('entity', models.ForeignKey(editable=False, to='creme_core.CremeEntity')),
                ('graph', models.ForeignKey(related_name='roots', editable=False, to='graphs.Graph')),
                ('relation_types', models.ManyToManyField(to='creme_core.RelationType', editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
