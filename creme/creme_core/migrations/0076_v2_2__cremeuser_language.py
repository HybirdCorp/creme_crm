from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0075_v2_2__customformconfigitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='language',
            field=models.CharField(
                verbose_name='Language', max_length=10,
                default='', blank=True,
                choices=[
                    ('',   'Language of your browser'),
                    ('en', 'English'),
                    ('fr', 'Français'),
                ],
            ),
        ),
    ]
