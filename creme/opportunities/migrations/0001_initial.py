from uuid import uuid4

from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CREME_REPLACE_NULL


class Migration(migrations.Migration):
    # replaces = [
    #     ('opportunities', '0001_initial'),
    #     ('opportunities', '0015_v2_5__salesphase_color01'),
    #     ('opportunities', '0016_v2_5__salesphase_color02'),
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
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                (
                    'color',
                    core_fields.ColorField(
                        verbose_name='Color',
                        default=core_fields.ColorField.random, max_length=6,
                    )
                ),
                ('won', models.BooleanField(default=False, verbose_name='Won')),
                ('lost', models.BooleanField(default=False, verbose_name='Lost')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
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
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        to='creme_core.CremeEntity', primary_key=True,
                        parent_link=True, auto_created=True, serialize=False,
                        on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the opportunity')),
                ('reference', models.CharField(max_length=100, verbose_name='Reference', blank=True)),
                ('estimated_sales', models.PositiveIntegerField(null=True, verbose_name='Estimated sales', blank=True)),
                ('made_sales', models.PositiveIntegerField(null=True, verbose_name='Made sales', blank=True)),
                ('chance_to_win', models.PositiveIntegerField(null=True, verbose_name='% of chance to win', blank=True)),
                ('expected_closing_date', models.DateField(null=True, verbose_name='Expected closing date', blank=True)),
                ('closing_date', models.DateField(null=True, verbose_name='Actual closing date', blank=True)),
                ('first_action_date', models.DateField(null=True, verbose_name='Date of the first action', blank=True)),
                ('currency', models.ForeignKey(on_delete=PROTECT, default=1, verbose_name='Currency', to='creme_core.Currency')),
                ('origin', models.ForeignKey(on_delete=CREME_REPLACE_NULL, verbose_name='Origin', blank=True, to='opportunities.Origin', null=True)),
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
