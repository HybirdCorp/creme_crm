from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0096_v2_4__job_results_entity_ctype02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entityjobresult',
            name='entity_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, null=True, on_delete=CASCADE,
            ),
        ),
        migrations.AlterField(
            model_name='massimportjobresult',
            name='entity_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, null=True, on_delete=CASCADE,
            ),
        ),
    ]
