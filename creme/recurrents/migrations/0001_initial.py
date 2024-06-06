from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import CASCADE

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    # Memo: last migration is '0008_v2_1__move_description_to_entity_3'

    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurrentGenerator',
            fields=[
                (
                    'cremeentity_ptr',
                    models.OneToOneField(
                        parent_link=True, auto_created=True, primary_key=True, serialize=False,
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                    )
                ),
                ('name', models.CharField(max_length=100, verbose_name='Name of the generator', blank=True)),
                ('first_generation', models.DateTimeField(verbose_name='Date of the first generation')),
                (
                    'last_generation',
                    models.DateTimeField(verbose_name='Date of the last generation', null=True, editable=False)
                ),
                ('periodicity', core_fields.DatePeriodField(verbose_name='Periodicity of the generation')),
                ('is_working', models.BooleanField(default=True, verbose_name='Active?', editable=False)),
                (
                    'ct',
                    core_fields.CTypeForeignKey(
                        to='contenttypes.ContentType',
                        editable=False, verbose_name='Type of the recurrent resource'
                    )
                ),
                (
                    'template',
                    models.ForeignKey(
                        to='creme_core.CremeEntity', on_delete=CASCADE,
                        related_name='template_set', editable=False,
                        verbose_name='Related model'
                    )
                ),
            ],
            options={
                'swappable': 'RECURRENTS_RGENERATOR_MODEL',
                'ordering': ('name',),
                'verbose_name': 'Recurrent generator',
                'verbose_name_plural': 'Recurrent generators',
            },
            bases=('creme_core.cremeentity',),
        ),
    ]

    if settings.TESTS_ON:
        operations.extend([
            migrations.CreateModel(
                name='FakeRecurrentDoc',
                fields=[
                    (
                        'cremeentity_ptr', models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=CASCADE,
                        )
                    ),
                    ('title', models.CharField(unique=True, max_length=50, verbose_name='Title')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Recurrent Document',
                    'verbose_name_plural': 'Test Recurrent Documents',
                },
                bases=('creme_core.cremeentity',),
            ),
            migrations.CreateModel(
                name='FakeRecurrentTemplate',
                fields=[
                    (
                        'cremeentity_ptr', models.OneToOneField(
                            parent_link=True, auto_created=True, primary_key=True, serialize=False,
                            to='creme_core.CremeEntity', on_delete=CASCADE,
                        )
                    ),
                    ('title', models.CharField(unique=True, max_length=50, verbose_name='Title')),
                ],
                options={
                    'ordering': ('title',),
                    'verbose_name': 'Test Recurrent Template',
                    'verbose_name_plural': 'Test Recurrent Templates',
                },
                bases=('creme_core.cremeentity',),
            ),
        ])
