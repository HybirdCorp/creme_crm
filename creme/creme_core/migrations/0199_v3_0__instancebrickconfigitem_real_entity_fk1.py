from django.db import migrations, models

from creme.creme_core.models import fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0198_v3_0__workflow_extra_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='instancebrickconfigitem',
            name='entity_ctype',
            field=core_fields.EntityCTypeForeignKey(
                null=True, default=None,  # <==
                to='contenttypes.contenttype', related_name='+',
                editable=False, on_delete=models.CASCADE,
            ),
            preserve_default=False,
        ),
    ]
