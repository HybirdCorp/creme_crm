from django.db import migrations, models
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import CTypeOneToOneField


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('billing', '0021_v2_2__line_vat_not_null2'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExporterConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_type', CTypeOneToOneField(on_delete=CASCADE, to='contenttypes.ContentType')),
                ('engine_id', models.CharField(max_length=80)),
                ('flavour_id', models.CharField(max_length=80, blank=True)),
            ],
        ),
    ]
