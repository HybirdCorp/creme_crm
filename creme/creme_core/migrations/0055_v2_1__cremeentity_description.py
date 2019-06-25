from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0054_v2_1__deletion_command'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeentity',
            name='description',
            field=models.TextField(blank=True, verbose_name='Description'),
        ),
    ]
