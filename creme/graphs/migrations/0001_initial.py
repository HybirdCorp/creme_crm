# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Graph',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the graph')),
                ('orbital_relation_types', models.ManyToManyField(to='creme_core.RelationType', editable=False, verbose_name='Types of the peripheral relations')),
            ],
            options={
                'swappable': 'GRAPHS_GRAPH_MODEL',
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
                ('entity', models.ForeignKey(editable=False, to='creme_core.CremeEntity', on_delete=CASCADE)),
                ('graph', models.ForeignKey(related_name='roots', editable=False, to=settings.GRAPHS_GRAPH_MODEL, on_delete=CASCADE)),
                ('relation_types', models.ManyToManyField(to='creme_core.RelationType', editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
