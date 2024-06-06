from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0147_v2_6__clean_button_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='settingvalue',
            name='json_value',
            field=models.JSONField(editable=False, null=True),
        ),
    ]
