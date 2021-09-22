# NB: this file should be named "0025_v2_ 3 __contact_languages01.py".
#     The following file is badly named too, but the error has been viewed lately...

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
