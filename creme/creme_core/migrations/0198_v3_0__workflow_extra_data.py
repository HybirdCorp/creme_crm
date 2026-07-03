from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0197_v3_0__populated_app'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
