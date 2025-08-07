from uuid import uuid4

from django.db import migrations, models
from django.db.models.deletion import CASCADE

import creme.creme_core.models.fields as core_fields
from creme.creme_core.models import CREME_REPLACE


class Migration(migrations.Migration):
    # Memo: last migration was "0015_v2_6__fix_uuids"
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Criticity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Ticket criticality',
                'verbose_name_plural': 'Ticket criticality',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Priority',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Ticket priority',
                'verbose_name_plural': 'Ticket priorities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('order', core_fields.BasicAutoField(editable=False, blank=True)),
                (
                    'is_closed',
                    models.BooleanField(
                        default=False,
                        verbose_name='Is a "closed" status?',
                        help_text=(
                            'If you set as closed, existing tickets which use this status will '
                            'not be updated automatically (i.e. closing dates will not be set).'
                        ),
                    )
                ),
                (
                    'color',
                    core_fields.ColorField(
                        verbose_name='Color',
                        default=core_fields.ColorField.random, max_length=6,
                    )
                ),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('uuid', models.UUIDField(default=uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Ticket status',
                'verbose_name_plural': 'Ticket statuses',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TicketNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('number', models.PositiveIntegerField(verbose_name='Number', unique=True, editable=False)),
                ('title', models.CharField(max_length=100, verbose_name='Title', blank=True)),
                ('solution', models.TextField(verbose_name='Solution', blank=True)),
                (
                    'closing_date',
                    models.DateTimeField(verbose_name='Closing date', null=True, editable=False, blank=True)
                ),
                (
                    'criticity',
                    models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Criticality', to='tickets.Criticity')
                ),
                (
                    'priority',
                    models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Priority', to='tickets.Priority')
                ),
                (
                    'status',
                    models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status', to='tickets.Status')
                ),
            ],
            options={
                'swappable': 'TICKETS_TICKET_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Ticket',
                'verbose_name_plural': 'Tickets',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='TicketTemplate',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('title', models.CharField(max_length=100, verbose_name='Title', blank=True)),
                ('solution', models.TextField(verbose_name='Solution', blank=True)),
                (
                    'criticity',
                    models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Criticality', to='tickets.Criticity')
                ),
                (
                    'priority',
                    models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Priority', to='tickets.Priority')
                ),
                (
                    'status',
                    models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Status', to='tickets.Status')
                ),
            ],
            options={
                'swappable': 'TICKETS_TEMPLATE_MODEL',
                'ordering': ('title',),
                'verbose_name': 'Ticket template',
                'verbose_name_plural': 'Ticket templates',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
