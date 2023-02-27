from django.db import migrations

from creme.creme_core.models.fields import ColorField


def generate_colors(apps, schema_editor):
    for model_name in ('InvoiceStatus', 'CreditNoteStatus', 'SalesOrderStatus'):
        for status in apps.get_model('billing', model_name).objects.all():
            status.color = ColorField.random()
            status.save()

    for status in apps.get_model('billing', 'QuoteStatus').objects.all():
        status.color = '1dd420' if status.won else ColorField.random()
        status.save()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0028_v2_5__colored_statuses01'),
    ]

    operations = [
        migrations.RunPython(generate_colors),
    ]
