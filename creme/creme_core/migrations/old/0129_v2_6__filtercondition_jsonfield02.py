from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0128_v2_6__filtercondition_jsonfield01'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entityfiltercondition',
            old_name='raw_value',
            new_name='value',
        ),
        migrations.AlterField(
            model_name='entityfiltercondition',
            name='value',
            field=models.JSONField(default=dict),
        ),
    ]
