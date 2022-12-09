from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0094_v2_4__semifixedrelationtype_object_ctype03'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityjobresult',
            name='entity_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                null=True, editable=False, on_delete=CASCADE,
                default=None,  # temporary
            ),
        ),
        migrations.AddField(
            model_name='massimportjobresult',
            name='entity_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, null=True, on_delete=CASCADE,
                default=None,  # temporary
            ),
        ),
    ]
