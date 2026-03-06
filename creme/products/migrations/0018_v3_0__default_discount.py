from decimal import Decimal

from django.db import migrations

import creme.creme_core.models.fields as core_fields


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='default_discount',
            field=core_fields.DecimalPercentField(
                verbose_name='Default discount',
                blank=True, max_digits=4, decimal_places=2, default=Decimal('0.00'),
                help_text='This value is used when creating lines for Invoices/Quotes/…',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='default_discount',
            field=core_fields.DecimalPercentField(
                verbose_name='Default discount',
                blank=True, max_digits=4, decimal_places=2, default=Decimal('0.00'),
                help_text='This value is used when creating lines for Invoices/Quotes/…',
            ),
        ),
    ]
