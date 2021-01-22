from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='status',
            name='is_closed',
            field=models.BooleanField(
                default=False,
                verbose_name='Is a "closed" status?',
                help_text=(
                    'If you set as closed, existing tickets which use this status will '
                    'not be updated automatically (ie: closing dates will not be set).'
                ),
            ),
        ),
    ]
