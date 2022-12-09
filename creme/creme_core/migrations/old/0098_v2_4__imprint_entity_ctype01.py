from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0097_v2_4__job_results_entity_ctype03'),
    ]

    operations = [
        migrations.AddField(
            model_name='imprint',
            name='entity_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, on_delete=CASCADE,
                null=True, default=None,  # Temporary
            ),
        ),
    ]
