from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lightweightemail',
            name='recipient_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, null=True, on_delete=CASCADE,
                default=None,  # temporary
            ),
        ),
    ]
