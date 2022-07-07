from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0111_v2_4__rtype_forbidden_properties'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuconfigitem',
            name='role',
            field=models.ForeignKey(
                default=None, editable=False, null=True,
                on_delete=CASCADE, to='creme_core.userrole'
            ),
        ),
        migrations.AddField(
            model_name='menuconfigitem',
            name='superuser',
            field=models.BooleanField(
                default=False, editable=False, verbose_name='related to superusers',
            ),
        ),
    ]
