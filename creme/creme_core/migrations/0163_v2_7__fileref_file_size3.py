from django.db import migrations

from creme.creme_core.models import fields


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0162_v2_7__fileref_file_size2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileref',
            name='file_size',
            field=fields.FileSizeField(editable=False, verbose_name='Size of the file'),
        ),
    ]
