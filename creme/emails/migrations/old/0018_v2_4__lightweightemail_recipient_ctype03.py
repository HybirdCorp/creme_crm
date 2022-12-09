from django.db import migrations
from django.db.models.deletion import CASCADE

from creme.creme_core.models.fields import EntityCTypeForeignKey


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('emails', '0017_v2_4__lightweightemail_recipient_ctype02'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lightweightemail',
            name='recipient_ctype',
            field=EntityCTypeForeignKey(
                to='contenttypes.contenttype', related_name='+',
                editable=False, null=True, on_delete=CASCADE,
            ),
        ),
    ]
