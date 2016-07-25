# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations

# NB: it seems PostGreSQL does like that we migrate CharFields directly
#     (ie: only '0004_v1_7__charfields_not_nullable_2.py')

PRODUCT_FIELDS = ['web_site']
SERVICE_FIELDS = ['web_site']


def fill_none_strings(apps, schema_editor):
    def migrate_model(setting_model, name, fields):
        if setting_model == 'products.%s' % name:
            manager = apps.get_model('products', name).objects

            for field_name in fields:
                manager.filter(**{field_name: None}).update(**{field_name: ''})

    migrate_model(settings.PRODUCTS_PRODUCT_MODEL, 'Product', PRODUCT_FIELDS)
    migrate_model(settings.PRODUCTS_SERVICE_MODEL, 'Service', SERVICE_FIELDS)


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0002_v1_6__fk_on_delete_set'),
    ]

    operations = [
        migrations.RunPython(fill_none_strings),
    ]
