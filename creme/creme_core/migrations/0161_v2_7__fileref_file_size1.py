from django.db import migrations

from creme.creme_core.models import fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0160_v2_7__customentitytype'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileref',
            name='file_size',
            field=fields.FileSizeField(
                default=None, editable=False, null=True, verbose_name='Size of the file',
            ),
        ),
    ]
