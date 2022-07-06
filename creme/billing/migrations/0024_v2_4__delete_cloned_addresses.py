from collections import defaultdict

from django.conf import settings
from django.db import migrations

MODELS_CONF = [
    ('BILLING_CREDIT_NOTE_MODEL',   'billing.CreditNote'),
    ('BILLING_INVOICE_MODEL',       'billing.Invoice'),
    ('BILLING_QUOTE_MODEL',         'billing.Quote'),
    ('BILLING_SALES_ORDER_MODEL',   'billing.SalesOrder'),
    ('BILLING_TEMPLATE_BASE_MODEL', 'billing.TemplateBase'),
]

def delete_addresses(apps, schema_editor):
    Address = apps.get_model('persons', 'Address')
    if not Address.objects.exists():
        return

    get_ct = apps.get_model('contenttypes', 'ContentType').objects.get

    for setting_name, model_key in MODELS_CONF:
        if getattr(settings, setting_name) == model_key:
            app_name, model_name = model_key.split('.')
            model = apps.get_model(app_name, model_name)
            stats = defaultdict(set)

            for addr_id, entity_id in Address.objects.filter(
                content_type=get_ct(app_label=app_name, model=model_name.lower()),
            ).values_list('id', 'object_id'):
                stats[entity_id].add(addr_id)

            for entity_id, addr_ids in stats.items():
                if len(addr_ids) == 4:
                    # Some useless addresses have been created (clone, conversion)
                    used_ids = {
                        addr_id
                        for addr_ids in model.objects.filter(id=entity_id).values_list(
                            'billing_address_id', 'shipping_address_id',
                        )[:1]
                        for addr_id in addr_ids
                    }
                    Address.objects.filter(id__in=addr_ids - used_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(delete_addresses),
    ]
