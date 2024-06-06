from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0149_v2_6__settingvalue_json02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='settingvalue',
            name='value_str',
        ),
    ]
