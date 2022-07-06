from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0093_v2_4__semifixedrelationtype_object_ctype02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='semifixedrelationtype',
            name='object_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, on_delete=CASCADE,
            ),
        ),
    ]
