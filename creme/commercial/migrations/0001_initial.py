import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT
from django.utils.timezone import now

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    # Memo: last migration was "0022_v2_6__settingvalue_json.py"
    initial = True
    dependencies = [
        ('contenttypes', '0001_initial'),
        ('creme_core', '0001_initial'),
        migrations.swappable_dependency(settings.PERSONS_ORGANISATION_MODEL),
        migrations.swappable_dependency(settings.ACTIVITIES_ACTIVITY_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketSegment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'property_type',
                    models.ForeignKey(
                        to='creme_core.CremePropertyType',
                        editable=False, null=True, on_delete=CASCADE,
                    )
                ),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Market segment',
                'verbose_name_plural': 'Market segments',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=75, verbose_name='Title')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Type of commercial action',
                'verbose_name_plural': 'Types of commercial actions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Act',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the commercial action')),
                ('expected_sales', models.PositiveIntegerField(verbose_name='Expected sales')),
                (
                    'cost',
                    models.PositiveIntegerField(
                        verbose_name='Cost of the commercial action', null=True, blank=True,
                    )
                ),
                ('goal', models.TextField(verbose_name='Goal of the action', blank=True)),
                ('start', models.DateField(verbose_name='Start')),
                ('due_date', models.DateField(verbose_name='Due date')),
                (
                    'segment',
                    models.ForeignKey(
                        to='commercial.MarketSegment',
                        on_delete=PROTECT, verbose_name='Related segment',
                    )
                ),
                ('act_type', models.ForeignKey(on_delete=PROTECT, verbose_name='Type', to='commercial.ActType')),
            ],
            options={
                'swappable': 'COMMERCIAL_ACT_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Commercial action',
                'verbose_name_plural': 'Commercial actions',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='ActObjective',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('counter', models.PositiveIntegerField(default=0, verbose_name='Counter', editable=False)),
                ('counter_goal', models.PositiveIntegerField(default=1, verbose_name='Value to reach')),
                (
                    'act',
                    models.ForeignKey(
                        to=settings.COMMERCIAL_ACT_MODEL,
                        related_name='objectives', editable=False, on_delete=CASCADE,
                    ),
                ),
                (
                    'ctype',
                    core_fields.CTypeForeignKey(
                        blank=True, editable=False, to='contenttypes.ContentType',
                        null=True, verbose_name='Counted type',
                    ),
                ),
                (
                    'filter',
                    models.ForeignKey(
                        to='creme_core.EntityFilter',
                        on_delete=PROTECT, blank=True, editable=False,
                        null=True, verbose_name='Filter on counted entities',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Commercial Objective',
                'verbose_name_plural': 'Commercial Objectives',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActObjectivePattern',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    ),
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('average_sales', models.PositiveIntegerField(verbose_name='Average sales')),
                (
                    'segment',
                    models.ForeignKey(
                        to='commercial.MarketSegment',
                        verbose_name='Related segment', on_delete=CASCADE,
                    ),
                ),
            ],
            options={
                'swappable': 'COMMERCIAL_PATTERN_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Objective pattern',
                'verbose_name_plural': 'Objective patterns',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='ActObjectivePatternComponent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('success_rate', models.PositiveIntegerField(verbose_name='Success rate')),
                (
                    'ctype',
                    core_fields.CTypeForeignKey(
                        to='contenttypes.ContentType', verbose_name='Counted type',
                        blank=True, editable=False, null=True,
                    )
                ),
                (
                    'filter',
                    models.ForeignKey(
                        on_delete=PROTECT, blank=True, editable=False, to='creme_core.EntityFilter',
                        null=True, verbose_name='Filter on counted entities',
                    )
                ),
                (
                    'parent',
                    models.ForeignKey(
                        related_name='children', editable=False,
                        to='commercial.ActObjectivePatternComponent', null=True, on_delete=CASCADE,
                    ),
                ),
                (
                    'pattern',
                    models.ForeignKey(
                        to=settings.COMMERCIAL_PATTERN_MODEL,
                        related_name='components', editable=False, on_delete=CASCADE,
                    )
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CommercialApproach',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name='Title')),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                (
                    'creation_date',
                    core_fields.CreationDateTimeField(
                        default=now, verbose_name='Creation date', editable=False, blank=True,
                    ),
                ),
                (
                    'entity',
                    models.ForeignKey(
                        to='creme_core.CremeEntity',
                        editable=False, on_delete=CASCADE, related_name='commercial_approaches',
                    ),
                ),
                (
                    'entity_content_type',
                    core_fields.EntityCTypeForeignKey(
                        to='contenttypes.ContentType',
                        editable=False, on_delete=CASCADE, related_name='+',
                    )
                ),
                (
                    'related_activity',
                    models.ForeignKey(
                        to=settings.ACTIVITIES_ACTIVITY_MODEL,
                        editable=False, null=True, on_delete=CASCADE,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Commercial approach',
                'verbose_name_plural': 'Commercial approaches',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Strategy',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'evaluated_orgas',
                    models.ManyToManyField(
                        to=settings.PERSONS_ORGANISATION_MODEL,
                        verbose_name='Evaluated organisation(s)', editable=False,
                    ),
                ),
            ],
            options={
                'swappable': 'COMMERCIAL_STRATEGY_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Commercial strategy',
                'verbose_name_plural': 'Commercial strategies',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='MarketSegmentDescription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('product',   models.TextField(verbose_name='Product',   blank=True)),
                ('place',     models.TextField(verbose_name='Place',     blank=True)),
                ('price',     models.TextField(verbose_name='Price',     blank=True)),
                ('promotion', models.TextField(verbose_name='Promotion', blank=True)),
                ('segment',   models.ForeignKey(to='commercial.MarketSegment', on_delete=CASCADE)),
                (
                    'strategy',
                    models.ForeignKey(
                        related_name='segment_info', editable=False,
                        to=settings.COMMERCIAL_STRATEGY_MODEL, on_delete=CASCADE,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Market segment description',
                'verbose_name_plural': 'Market segment descriptions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CommercialAsset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'strategy',
                    models.ForeignKey(
                        to=settings.COMMERCIAL_STRATEGY_MODEL,
                        related_name='assets', editable=False, on_delete=CASCADE,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Commercial asset',
                'verbose_name_plural': 'Commercial assets',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CommercialAssetScore',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', models.PositiveSmallIntegerField()),
                ('asset', models.ForeignKey(to='commercial.CommercialAsset', on_delete=CASCADE)),
                ('organisation', models.ForeignKey(to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)),
                ('segment_desc', models.ForeignKey(to='commercial.MarketSegmentDescription', on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MarketSegmentCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.PositiveSmallIntegerField()),
                ('organisation', models.ForeignKey(to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)),
                ('strategy', models.ForeignKey(to=settings.COMMERCIAL_STRATEGY_MODEL, on_delete=CASCADE)),
                ('segment_desc', models.ForeignKey(to='commercial.MarketSegmentDescription', on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MarketSegmentCharm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                (
                    'strategy',
                    models.ForeignKey(
                        to=settings.COMMERCIAL_STRATEGY_MODEL,
                        related_name='charms', editable=False, on_delete=CASCADE,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Segment charm',
                'verbose_name_plural': 'Segment charms',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MarketSegmentCharmScore',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', models.PositiveSmallIntegerField()),
                ('charm', models.ForeignKey(to='commercial.MarketSegmentCharm', on_delete=CASCADE)),
                ('organisation', models.ForeignKey(to=settings.PERSONS_ORGANISATION_MODEL, on_delete=CASCADE)),
                ('segment_desc', models.ForeignKey(to='commercial.MarketSegmentDescription', on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
    ]
