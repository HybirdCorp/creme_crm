from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0164_v2_7__cremeuser_uuid03'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileref',
            name='filedata',
            field=models.FileField(max_length=500, upload_to='', verbose_name='Path'),
        ),
    ]
