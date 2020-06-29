from decimal import Decimal

from django.conf import settings
from django.db import migrations


def convert_old_lines(apps, line_model):
    lines = line_model.objects.filter(vat_value=None)

    if lines.exists():
        vat = apps.get_model('creme_core', 'Vat').objects.get_or_create(value=Decimal('0'))[0]
        lines.update(vat_value=vat)


def convert_old_vat(apps, schema_editor):
    if settings.BILLING_PRODUCT_LINE_MODEL == 'billing.ProductLine':
        convert_old_lines(apps, apps.get_model('billing', 'ProductLine'))

    if settings.BILLING_SERVICE_LINE_MODEL == 'billing.ServiceLine':
        convert_old_lines(apps, apps.get_model('billing', 'ServiceLine'))


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0019_v2_2__discount02'),
    ]

    operations = [
        migrations.RunPython(convert_old_vat),
    ]
