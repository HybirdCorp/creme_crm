from django.db import migrations, models

from creme.creme_core.models import fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('creme_core', '0200_v3_0__instancebrickconfigitem_real_entity_fk2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instancebrickconfigitem',
            name='entity_ctype',
            field=core_fields.EntityCTypeForeignKey(
                to='contenttypes.contenttype',
                editable=False, on_delete=models.CASCADE, related_name='+',
            ),
        ),
    ]
