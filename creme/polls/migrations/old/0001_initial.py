import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL

import creme.polls.models.base


class Migration(migrations.Migration):
    # replaces = [
    #     ('polls', '0001_initial'),
    #     ('polls', '0004_v2_4__minion_type01'),
    #     ('polls', '0005_v2_4__minion_type02'),
    #     ('polls', '0006_v2_4__minion_type03'),
    # ]

    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
        ('commercial', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PollType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80, verbose_name='Name')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Type of poll',
                'verbose_name_plural': 'Types of poll',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PollCampaign',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('goal', models.TextField(verbose_name='Goal of the campaign', blank=True)),
                ('start', models.DateField(null=True, verbose_name='Start', blank=True)),
                ('due_date', models.DateField(null=True, verbose_name='Due date', blank=True)),
                ('expected_count', models.PositiveIntegerField(default=1, verbose_name='Expected replies number')),
                ('segment', models.ForeignKey(on_delete=PROTECT, verbose_name='Related segment', blank=True, to='commercial.MarketSegment', null=True)),
            ],
            options={
                'swappable': 'POLLS_CAMPAIGN_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Campaign of polls',
                'verbose_name_plural': 'Campaigns of polls',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='PollForm',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=220, verbose_name='Name')),
                ('type', models.ForeignKey(on_delete=SET_NULL, verbose_name='Type', blank=True, to='polls.PollType', null=True)),
            ],
            options={
                'swappable': 'POLLS_FORM_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Form of poll',
                'verbose_name_plural': 'Forms of poll',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='PollFormSection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False)),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('body', models.TextField(verbose_name='Section body', blank=True)),
                ('parent', models.ForeignKey(editable=False, to='polls.PollFormSection', null=True, on_delete=CASCADE)),
                ('pform', models.ForeignKey(related_name='sections', editable=False, to=settings.POLLS_FORM_MODEL, on_delete=CASCADE)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Section',
                'verbose_name_plural': 'Sections',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PollFormLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False)),
                ('disabled', models.BooleanField(default=False, editable=False)),
                ('type', models.PositiveSmallIntegerField(verbose_name='Type')),
                ('type_args', models.TextField(null=True, editable=False)),
                # ('conds_use_or', models.NullBooleanField(verbose_name='Use OR or AND between conditions', editable=False)),
                ('conds_use_or', models.BooleanField(verbose_name='Use OR or AND between conditions', editable=False, null=True)),
                ('question', models.TextField(verbose_name='Question')),
                ('pform', models.ForeignKey(related_name='lines', editable=False, to=settings.POLLS_FORM_MODEL, on_delete=CASCADE)),
                ('section', models.ForeignKey(editable=False, to='polls.PollFormSection', null=True, on_delete=CASCADE)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Question',
                'verbose_name_plural': 'Questions',
            },
            bases=(models.Model, creme.polls.models.base._PollLine),
        ),
        migrations.CreateModel(
            name='PollFormLineCondition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('operator', models.PositiveSmallIntegerField()),
                ('raw_answer', models.TextField(null=True)),
                ('line', models.ForeignKey(related_name='conditions', editable=False, to='polls.PollFormLine', on_delete=CASCADE)),
                ('source', models.ForeignKey(to='polls.PollFormLine', on_delete=CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PollReply',
            fields=[
                ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                         to='creme_core.CremeEntity', on_delete=CASCADE,
                                                        )
                ),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('is_complete', models.BooleanField(default=False, verbose_name='Is complete', editable=False)),
                ('campaign', models.ForeignKey(on_delete=PROTECT, verbose_name='Related campaign', blank=True, to=settings.POLLS_CAMPAIGN_MODEL, null=True)),
                ('person', models.ForeignKey(related_name='+', on_delete=PROTECT, verbose_name='Person who filled', blank=True, to='creme_core.CremeEntity', null=True)),
                ('pform', models.ForeignKey(on_delete=PROTECT, editable=False, to=settings.POLLS_FORM_MODEL, verbose_name='Related form')),
                ('type', models.ForeignKey(on_delete=SET_NULL, blank=True, editable=False, to='polls.PollType', null=True, verbose_name='Type')),
            ],
            options={
                'swappable': 'POLLS_REPLY_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Form reply',
                'verbose_name_plural': 'Form replies',
            },
            bases=('creme_core.cremeentity',),
        ),
        migrations.CreateModel(
            name='PollReplySection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False)),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('body', models.TextField(verbose_name='Section body', blank=True)),
                ('parent', models.ForeignKey(editable=False, to='polls.PollReplySection', null=True, on_delete=CASCADE)),
                ('preply', models.ForeignKey(related_name='sections', editable=False, to=settings.POLLS_REPLY_MODEL, on_delete=CASCADE)),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Section',
                'verbose_name_plural': 'Sections',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PollReplyLine',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=1, editable=False)),
                ('type', models.PositiveSmallIntegerField(editable=False)),
                ('type_args', models.TextField(null=True, editable=False)),
                ('applicable', models.BooleanField(default=True, verbose_name='Applicable', editable=False)),
                # ('conds_use_or', models.NullBooleanField(verbose_name='Use OR or AND between conditions', editable=False)),
                ('conds_use_or', models.BooleanField(verbose_name='Use OR or AND between conditions', editable=False, null=True)),
                ('question', models.TextField(verbose_name='Question')),
                ('raw_answer', models.TextField(null=True, verbose_name='Answer')),
                ('pform_line', models.ForeignKey(editable=False, to='polls.PollFormLine', on_delete=CASCADE)),
                ('preply', models.ForeignKey(related_name='lines', editable=False, to=settings.POLLS_REPLY_MODEL, on_delete=CASCADE)),
                ('section', models.ForeignKey(editable=False, to='polls.PollReplySection', null=True, on_delete=CASCADE)),
            ],
            options={
                'ordering': ('order',),
            },
            bases=(models.Model, creme.polls.models.base._PollLine),
        ),
        migrations.CreateModel(
            name='PollReplyLineCondition',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('operator', models.PositiveSmallIntegerField()),
                ('raw_answer', models.TextField(null=True)),
                ('line', models.ForeignKey(related_name='conditions', editable=False, to='polls.PollReplyLine', on_delete=CASCADE)),
                ('source', models.ForeignKey(to='polls.PollReplyLine', on_delete=CASCADE)),
            ],
            options={},
            bases=(models.Model,),
        ),
    ]
