from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0122_v2_5__cremeuser_displayed_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='worldsettings',
            name='user_name_change_enabled',
            field=models.BooleanField(
                default=True,
                verbose_name='Can users change their own displayed name?',
            ),
        ),
    ]
