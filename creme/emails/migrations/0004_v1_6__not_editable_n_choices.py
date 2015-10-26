# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('emails', '0003_v1_6__fk_on_delete_set'),
    ]

    operations = [
        # EntityEmail
        migrations.AlterField(
            model_name='entityemail',
            name='reads',
            field=models.PositiveIntegerField(default=0, verbose_name='Number of reads', null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='entityemail',
            name='reception_date',
            field=models.DateTimeField(verbose_name='Reception date', null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='entityemail',
            name='sending_date',
            field=models.DateTimeField(verbose_name='Sending date', null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='entityemail',
            name='status',
            field=models.PositiveSmallIntegerField(default=2, verbose_name='Status', editable=False,
                                                   choices=[(1, 'Sent'), (2, 'Not sent'), (3, 'Sending error'),
                                                            (4, 'Synchronized'), (5, 'Synchronized - Marked as SPAM'), (6, 'Synchronized - Untreated'),
                                                           ],
                                                  ),
        ),

        # LightweightEmail
        migrations.AlterField(
            model_name='lightweightemail',
            name='reads',
            field=models.PositiveIntegerField(default=0, verbose_name='Number of reads', null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='lightweightemail',
            name='reception_date',
            field=models.DateTimeField(verbose_name='Reception date', null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='lightweightemail',
            name='sending_date',
            field=models.DateTimeField(verbose_name='Sending date', null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='lightweightemail',
            name='status',
            field=models.PositiveSmallIntegerField(default=2, verbose_name='Status', editable=False,
                                                   choices=[(1, 'Sent'), (2, 'Not sent'), (3, 'Sending error'),
                                                            (4, 'Synchronized'), (5, 'Synchronized - Marked as SPAM'), (6, 'Synchronized - Untreated'),
                                                           ],
                                                  ),
        ),

        # EmailSending
        migrations.AlterField(
            model_name='emailsending',
            name='state',
            field=models.PositiveSmallIntegerField(default=3, verbose_name='Sending state', editable=False,
                                                   choices=[(1, 'Done'), (2, 'In progress'), (3, 'Planned'), (4, 'Error during sending')],
                                                  ),
        ),
        migrations.AlterField(
            model_name='emailsending',
            name='type',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Sending type', choices=[(1, 'Immediate'), (2, 'Deferred')]),
        ),
    ]
