from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0017_v2_8__reportchart02'),
    ]

    operations = [
        migrations.DeleteModel(name='ReportGraph'),
    ]
