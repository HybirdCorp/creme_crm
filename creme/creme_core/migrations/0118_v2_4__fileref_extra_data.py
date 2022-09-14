from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0117_v2_4__minion_models03'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileref',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
