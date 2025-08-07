from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    # Memo: last migration was "0005_v2_6__settingvalue_json".

    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.PERSONS_ADDRESS_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GeoAddress',
            fields=[
                (
                    'address',
                    models.OneToOneField(
                        to=settings.PERSONS_ADDRESS_MODEL, primary_key=True, verbose_name='Address',
                        serialize=False, on_delete=CASCADE,
                    )
                ),
                ('latitude', models.FloatField(null=True, verbose_name='Latitude', blank=True)),
                ('longitude', models.FloatField(null=True, verbose_name='Longitude', blank=True)),
                ('draggable', models.BooleanField(default=True, verbose_name='Is this marker draggable in maps?')),
                ('geocoded', models.BooleanField(default=False, verbose_name='Geocoded from address?')),
                (
                    'status',
                    models.SmallIntegerField(
                        default=0, verbose_name='Status',
                        choices=[
                            (0, 'Not localized'),
                            (1, 'Manual location'),
                            (2, 'Partially matching location'),
                            (3, ''),
                        ],
                    )
                ),
            ],
            options={
                'verbose_name': 'Address',
                'verbose_name_plural': 'Addresses',
                'ordering': ('address_id',)
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Town',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name of the town')),
                ('slug', models.SlugField(max_length=100, verbose_name='Slugified name of the town')),
                ('zipcode', models.CharField(max_length=100, verbose_name='Zip code', blank=True)),
                ('country', models.CharField(max_length=40, verbose_name='Country', blank=True)),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
            ],
            options={
                'verbose_name': 'Town',
                'verbose_name_plural': 'Towns',
                'ordering': ('name',)
            },
            bases=(models.Model,),
        ),
    ]
