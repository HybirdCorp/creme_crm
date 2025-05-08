from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0036_v2_7__organisation_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='eori',
            field=models.CharField(
                max_length=17, verbose_name='EORI number', blank=True,
                help_text='Economic Operators Registration and Identification number. Required for customs clearance in the EU.',
            ),
        ),
    ]
