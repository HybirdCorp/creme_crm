from django.db import migrations, models

from creme.creme_core.models.deletion import CREME_REPLACE_NULL


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='creditnote',
            name='payment_type',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                to='billing.settlementterms', verbose_name='Settlement terms'
            ),
        ),
        migrations.AddField(
            model_name='quote',
            name='payment_type',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                to='billing.settlementterms', verbose_name='Settlement terms',
            ),
        ),
        migrations.AddField(
            model_name='salesorder',
            name='payment_type',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                to='billing.settlementterms', verbose_name='Settlement terms',
            ),
        ),
        migrations.AddField(
            model_name='templatebase',
            name='payment_type',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=CREME_REPLACE_NULL,
                to='billing.settlementterms', verbose_name='Settlement terms',
            ),
        ),
    ]
