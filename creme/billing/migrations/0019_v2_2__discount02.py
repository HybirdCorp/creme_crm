from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0018_v2_2__discount01'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productline',
            name='total_discount',
        ),
        migrations.RemoveField(
            model_name='serviceline',
            name='total_discount',
        ),
        migrations.AlterField(
            model_name='productline',
            name='discount_unit',
            field=models.PositiveIntegerField(verbose_name='Discount Unit',
                                              choices=[(1, 'Percent'),
                                                       (2, 'Amount per line'),
                                                       (3, 'Amount per unit'),
                                                      ],
                                              default=1,
                                             ),
        ),
        migrations.AlterField(
            model_name='serviceline',
            name='discount_unit',
            field=models.PositiveIntegerField(verbose_name='Discount Unit',
                                              choices=[(1, 'Percent'),
                                                       (2, 'Amount per line'),
                                                       (3, 'Amount per unit'),
                                                      ],
                                              default=1,
                                             ),
        ),
    ]
