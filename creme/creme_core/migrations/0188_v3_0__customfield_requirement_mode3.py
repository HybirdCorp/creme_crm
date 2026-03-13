from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0187_v3_0__customfield_requirement_mode2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customfield',
            name='is_required',
        ),
    ]
