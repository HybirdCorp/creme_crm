from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0205_v3_0__entityfilter_disabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrole',
            name='deactivation_reason',
            field=models.TextField(default='', editable=False),
            preserve_default=False,
        ),
    ]
