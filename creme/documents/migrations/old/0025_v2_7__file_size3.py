from django.db import migrations

from creme.creme_core.models import fields as core_field


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0024_v2_7__file_size2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='file_size',
            field=core_field.FileSizeField(editable=False, verbose_name='Size of the file'),
        ),
    ]
