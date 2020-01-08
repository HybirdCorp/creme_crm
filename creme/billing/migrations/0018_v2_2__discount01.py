from django.conf import settings
from django.db import migrations


DISCOUNT_PERCENT     = 1
DISCOUNT_LINE_AMOUNT = 2
DISCOUNT_ITEM_AMOUNT = 3


def convert_old_lines(line_model):
    line_model.objects.filter(discount_unit=None).update(discount_unit=DISCOUNT_PERCENT)
    line_model.objects.filter(discount_unit=DISCOUNT_LINE_AMOUNT,
                              total_discount=False,
                             ).update(discount_unit=DISCOUNT_ITEM_AMOUNT)


def convert_old_discount(apps, schema_editor):
    if settings.BILLING_PRODUCT_LINE_MODEL == 'billing.ProductLine':
        convert_old_lines(apps.get_model('billing', 'ProductLine'))

    if settings.BILLING_SERVICE_LINE_MODEL == 'billing.ServiceLine':
        convert_old_lines(apps.get_model('billing', 'ServiceLine'))


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convert_old_discount),
    ]
