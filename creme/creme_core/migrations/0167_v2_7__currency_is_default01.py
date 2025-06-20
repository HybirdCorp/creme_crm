from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0166_v2_7__workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='Is default?'),
        ),
    ]
