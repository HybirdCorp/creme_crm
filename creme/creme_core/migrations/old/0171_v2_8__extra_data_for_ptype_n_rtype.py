from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0170_v2_8__userrole_listable_ctypes'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremepropertytype',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AddField(
            model_name='relationtype',
            name='extra_data',
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
