import uuid

from django.db import migrations, models
from django.db.models.deletion import CASCADE

from creme.creme_core.models import CREME_REPLACE


class Migration(migrations.Migration):
    # Memo: last migration was "0008_v2_6__fix_event_type_uuids.py"
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('extra_data', models.JSONField(default=dict, editable=False)),
                ('is_custom', models.BooleanField(default=True, editable=False)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Type of event',
                'verbose_name_plural': 'Types of event',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('place', models.CharField(max_length=100, verbose_name='Place', blank=True)),
                ('start_date', models.DateTimeField(verbose_name='Start date')),
                ('end_date', models.DateTimeField(null=True, verbose_name='End date', blank=True)),
                ('budget', models.DecimalField(null=True, verbose_name='Budget (\u20ac)', max_digits=10, decimal_places=2, blank=True)),
                ('final_cost', models.DecimalField(null=True, verbose_name='Final cost (\u20ac)', max_digits=10, decimal_places=2, blank=True)),
                ('type', models.ForeignKey(on_delete=CREME_REPLACE, verbose_name='Type', to='events.EventType')),
            ],
            options={
                'swappable': 'EVENTS_EVENT_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Event',
                'verbose_name_plural': 'Events',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]
