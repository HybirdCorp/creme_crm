from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0123_v2_5__worldsettings_user_name_change_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeentity',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
