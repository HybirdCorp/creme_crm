from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0180_v2_8__userrole_raw_special_perms'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrole',
            name='deactivated_on',
            field=models.DateTimeField(
                verbose_name='Deactivated on',
                default=None, editable=False, null=True,
            ),
        ),
    ]
