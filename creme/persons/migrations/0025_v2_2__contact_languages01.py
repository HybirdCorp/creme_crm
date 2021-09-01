from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0083_v2_2__remove_language_code'),
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contact',
            old_name='language',
            new_name='languages',
        ),
        migrations.AlterField(
            model_name='contact',
            name='languages',
            field=models.ManyToManyField(
                blank=True, to='creme_core.Language',
                verbose_name='Spoken language(s)',
            ),
        ),
    ]
