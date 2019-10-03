from django.db import migrations, models
from django.db.models import deletion

from creme.creme_core.models.fields import CTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0059_v2_1__convert_old_filter_format'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityfilter',
            name='filter_type',
            field=models.PositiveSmallIntegerField(
                choices=[(0, 'System filter (internal use)'),
                         (1, 'Regular filter (usable in list-view...'),
                        ],
                default=1,
                editable=False,
            ),
        ),
        migrations.AddField(
            model_name='setcredentials',
            name='efilter',
            field=models.ForeignKey(editable=False, null=True, on_delete=deletion.PROTECT, to='creme_core.EntityFilter'),
        ),
        migrations.AlterField(
            model_name='setcredentials',
            name='ctype',
            field=CTypeForeignKey(
                blank=True, null=True,
                on_delete=deletion.CASCADE,
                to='contenttypes.ContentType',
                verbose_name='Apply to a specific type',
            ),
        ),
        migrations.AlterField(
            model_name='setcredentials',
            name='forbidden',
            field=models.BooleanField(
                choices=[(False, 'The users are allowed to perform the selected actions'),
                         (True, 'The users are NOT allowed to perform the selected actions'),
                        ],
                default=False,
                help_text='Notice that actions which are forbidden & allowed at the same time are considered as forbidden when final permissions are computed.',
                verbose_name='Allow or forbid?',
            ),
        ),
        migrations.AlterField(
            model_name='setcredentials',
            name='set_type',
            field=models.PositiveIntegerField(
                choices=[(1, 'All entities'),
                         (2, "User's own entities"),
                         (3, 'Filtered entities')
                        ],
                default=1,
                help_text='The choice «Filtered entities» allows to configure credentials based on values of fields or relationships for example.',
                verbose_name='Type of entities set',
            ),
        ),
    ]
