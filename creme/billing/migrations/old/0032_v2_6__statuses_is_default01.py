from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditnotestatus',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='Is default?'),
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='Is default?'),
        ),
        migrations.AddField(
            model_name='invoicestatus',
            name='is_validated',
            field=models.BooleanField(
                default=False, verbose_name='Is validated?',
                help_text='If true, the status is used when an Invoice number is generated.',
            ),
        ),
        migrations.AddField(
            model_name='quotestatus',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='Is default?'),
        ),
        migrations.AddField(
            model_name='salesorderstatus',
            name='is_default',
            field=models.BooleanField(default=False, verbose_name='Is default?'),
        ),
    ]
