from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0088_v2_3__customforms_per_role02'),
    ]

    operations = [
        migrations.DeleteModel(name='OldCustomFormConfigItem'),
    ]
