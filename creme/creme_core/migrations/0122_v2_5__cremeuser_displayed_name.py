from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0121_v2_5__django42_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='cremeuser',
            name='displayed_name',
            field=models.CharField(
                max_length=50, verbose_name='Displayed name', blank=True,
                help_text=(
                    'If you do not fill this field, an automatic name will be used '
                    '(«John Doe» will be displayed as «John D.»).'
                ),
            ),
        ),
    ]
