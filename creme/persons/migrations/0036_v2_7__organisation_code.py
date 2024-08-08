from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='code',
            field=models.CharField(
                max_length=30, verbose_name='Code', blank=True,
                help_text='Useful to distinguish your managed organisations',
            ),
        ),
    ]
