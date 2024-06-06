from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0150_v2_6__settingvalue_json03'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityfilter',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='headerfilter',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
