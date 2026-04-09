from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0190_v3_0__efilter_condition_string_types2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='entityfiltercondition',
            name='old_type',
        ),
    ]
