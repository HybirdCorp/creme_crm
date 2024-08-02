from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='floating_type',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Fixed'), (2, 'Floating time'), (3, 'Floating')],
                default=1, editable=False, verbose_name='Fixed or floating?',
            ),
        ),
    ]
