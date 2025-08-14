from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0018_v2_8__reportchart03'),
    ]

    operations = [
        migrations.DeleteModel(name='ReportGraph'),
    ]
