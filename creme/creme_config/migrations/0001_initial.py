# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = []

    if settings.TESTS_ON:
        operations.extend([
            migrations.CreateModel(
                name='FakeConfigEntity',
                fields=[
                    ('cremeentity_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                                             to='creme_core.CremeEntity', on_delete=models.CASCADE,
                                                            )
                    ),
                    ('name', models.CharField(max_length=100, verbose_name='Name')),
                ],
                options={
                    'ordering': ('name',),
                    'verbose_name': 'Test ConfigEntity',
                    'verbose_name_plural': 'Test ConfigEntities',
                },
                bases=('creme_core.cremeentity',),
            ),
        ])
