from django.conf import settings
from django.db import migrations
# from django.db.models.expressions import F


def copy_description(apps, schema_editor):
    # NB: <F('description_tmp')> does not work, only see the fields of CremeEntity
    if settings.PRODUCTS_PRODUCT_MODEL == 'products.Product':
        # apps.get_model('products', 'Product').objects.update(description=F('description_tmp'))
        for product in apps.get_model('products', 'Product').objects.exclude(description_tmp=''):
            product.description = product.description_tmp
            product.save()

    if settings.PRODUCTS_SERVICE_MODEL == 'products.Service':
        # apps.get_model('products', 'Service').objects.update(description=F('description_tmp'))
        for service in apps.get_model('products', 'Service').objects.exclude(description_tmp=''):
            service.description = service.description_tmp
            service.save()


class Migration(migrations.Migration):
    dependencies = [
        ('products',   '0009_v2_1__move_description_to_entity_1'),
        ('creme_core', '0055_v2_1__cremeentity_description'),
    ]

    operations = [
        migrations.RunPython(copy_description),
    ]
