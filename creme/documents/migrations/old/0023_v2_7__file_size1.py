from django.db import migrations

from creme.creme_core.models import fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='file_size',
            field=core_fields.FileSizeField(
                default=None, editable=False, null=True, verbose_name='Size of the file',
            ),
        ),
    ]
