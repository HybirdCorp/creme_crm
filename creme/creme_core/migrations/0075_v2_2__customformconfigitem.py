from django.db import migrations, models
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import CTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0074_v2_2__buttonmenuitem_int_id03'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomFormConfigItem',
            fields=[
                ('cform_id', models.CharField(editable=False, max_length=100, primary_key=True, serialize=False)),
                ('json_groups', models.TextField(editable=False, null=True)),
            ],
        ),
    ]
