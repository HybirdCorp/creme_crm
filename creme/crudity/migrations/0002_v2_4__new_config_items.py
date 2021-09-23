# -*- coding: utf-8 -*-

from django.db import migrations, models
from django.db.models import deletion

from creme.creme_core.models.fields import CTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('crudity', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FetcherConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_id', models.TextField()),
                ('options', models.JSONField(default=dict)),
            ],
            options={
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='MachineConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'action_type',
                    models.PositiveSmallIntegerField(
                        verbose_name='Action type',
                        choices=[(1, 'Create'), (2, 'Update'), (3, 'Delete')],
                    )
                ),
                ('json_extractors', models.JSONField(default=list)),
                (
                    'content_type',
                    CTypeForeignKey(
                        verbose_name='Resource type',
                        to='contenttypes.contenttype',
                        on_delete=deletion.CASCADE,
                    )
                ),
                ('fetcher_item', models.ForeignKey(on_delete=deletion.PROTECT, to='crudity.fetcherconfigitem')),
            ],
        ),
    ]
