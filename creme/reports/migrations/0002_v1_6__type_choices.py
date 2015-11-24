# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportgraph',
            name='abscissa',
            field=models.CharField(verbose_name='X axis', max_length=100, editable=False),
        ),
        migrations.AlterField(
            model_name='reportgraph',
            name='ordinate',
            field=models.CharField(verbose_name='Y axis', max_length=100, editable=False),
        ),
        migrations.AlterField(
            model_name='reportgraph',
            name='type',
            field=models.PositiveIntegerField(verbose_name='Grouping', editable=False,
                                              choices=[(1, 'By days'), (2, 'By months'), (3, 'By years'), (4, 'By X days'),
                                                       (5, 'By values'), (6, 'By values (of related entities)'),
                                                       (11, 'By days (custom field)'), (12, 'By months (custom field)'),
                                                       (13, 'By years (custom field)'), (14, 'By X days (custom field)'),
                                                       (15, 'By values (of custom choices)'),
                                                      ],
                                             ),
        ),
    ]
