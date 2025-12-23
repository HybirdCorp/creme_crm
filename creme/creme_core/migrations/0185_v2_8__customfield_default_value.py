from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0184_v2_8__pinned_entity'),
    ]

    operations = [
        migrations.AddField(
            model_name='customfield',
            name='json_default_value_maker',
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
