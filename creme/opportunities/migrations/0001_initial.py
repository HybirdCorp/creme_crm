from uuid import uuid4

from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CREME_REPLACE_NULL
from creme.creme_core.models.currency import get_default_currency_pk


class Migration(migrations.Migration):
    # Memo: last migration was "0018_v2_6__settingvalue_json"
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
                ('chance_to_win', core_fields.IntegerPercentField(null=True, verbose_name='Chance to win', blank=True)),
                ('expected_closing_date', models.DateField(null=True, verbose_name='Expected closing date', blank=True)),
                ('closing_date', models.DateField(null=True, verbose_name='Actual closing date', blank=True)),
                ('first_action_date', models.DateField(null=True, verbose_name='Date of the first action', blank=True)),
                (
                    'currency',
                    models.ForeignKey(
                        verbose_name='Currency', to='creme_core.Currency',
                        on_delete=PROTECT,
                        default=get_default_currency_pk,
                    )
                ),
                (
                    'origin',
                    models.ForeignKey(
                        verbose_name='Origin', to='opportunities.Origin',
                        on_delete=CREME_REPLACE_NULL, blank=True, null=True,
                    )
                ),
                (
                    'sales_phase',
                    models.ForeignKey(
                        verbose_name='Sales phase', to='opportunities.SalesPhase',
                        on_delete=PROTECT,
                    )
                ),
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
