from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    # Memo: last migration was "0005_v2_4__graph_brick_in_old_configs"
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Graph',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True, on_delete=CASCADE,
                        parent_link=True, auto_created=True, serialize=False,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the graph')),
                (
                    'orbital_relation_types',
                    models.ManyToManyField(
                        verbose_name='Types of the peripheral relations',
                        to='creme_core.RelationType', editable=False,
                    )
                ),
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
                (
                    'entity_ctype',
                    EntityCTypeForeignKey(
                        to='contenttypes.contenttype', related_name='+',
                        editable=False, on_delete=CASCADE,
                    )
                ),
                ('entity', models.ForeignKey(editable=False, to='creme_core.CremeEntity', on_delete=CASCADE)),
                (
                    'graph',
                    models.ForeignKey(
                        to=settings.GRAPHS_GRAPH_MODEL,
                        related_name='roots', editable=False, on_delete=CASCADE,
                    )
                ),
                ('relation_types', models.ManyToManyField(to='creme_core.RelationType', editable=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
