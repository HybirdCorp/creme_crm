from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('graphs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='rootnode',
            name='entity_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, on_delete=CASCADE,
                null=True, default=None,  # <= temporary
            ),
        ),
    ]
