# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from json import loads as json_load, dumps as json_dump

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import migrations, models


def _get_model(apps, model_setting, app_label, model_name):
    model = None

    if model_setting == '%s.%s' % (app_label, model_name):
        model = apps.get_model(app_label, model_name)
    else:
        concrete_app_label, concrete_model_name = model_setting.split('.')
        concrete_model = apps.get_model(concrete_app_label, concrete_model_name)

        try:
            img_field = concrete_model._meta.get_field('images')
        except FieldDoesNotExist:
            pass
        else:
            if isinstance(img_field, models.ManyToManyField) and \
               img_field.rel.to == apps.get_model('media_managers', 'Image'):
                model = concrete_model

    return model


def _get_ctypes(apps):
    ctypes = []
    ContentType = apps.get_model('contenttypes', 'ContentType')

    def _get_ct(model_setting, app_label, model_name):
        ct_app_label, ct_model = model_setting.split('.')

        if _get_model(apps, model_setting, app_label, model_name) is None:
            return None

        ct = ContentType.objects \
                        .filter(app_label=ct_app_label, model=ct_model.lower()) \
                        .first()

        return None if ct is None else (ct_model, ct)

    product_info = _get_ct(settings.PRODUCTS_PRODUCT_MODEL, 'products', 'Product')
    if product_info is not None:
        ctypes.append(product_info)

    service_info = _get_ct(settings.PRODUCTS_SERVICE_MODEL, 'products', 'Service')
    if service_info is not None:
        ctypes.append(service_info)

    return ctypes


def _update_cells(cells, instance, related_model_name):
    save = False

    for cell in cells:
        if cell['type'] != 'regular_field':
            continue

        fname = cell['value']
        if fname == 'images__name':
            cell['value'] = 'images__title'
            save = True
        elif fname == 'images__image':
            cell['value'] = 'images__filedata'
            save = True
        elif fname in ('images__height', 'images__width'):
            print('The %s id="%s" (for <%s>) use a removed field Image.height/width.' % (
                        instance.__class__.__name__,
                        instance.id,
                        related_model_name,
                    )
                 )

    return save


def replace_img_m2m(apps, schema_editor):
    # get_model = apps.get_model
    #
    # if settings.PRODUCTS_PRODUCT_MODEL == 'products.Product':
    #     for product in get_model('products', 'Product').objects.filter(images__isnull=False):
    #         product.images_tmp = list(product.images.values_list('id', flat=True))
    #
    # if settings.PRODUCTS_SERVICE_MODEL == 'products.Service':
    #     for service in get_model('products', 'Service').objects.filter(images__isnull=False):
    #         service.images_tmp = list(service.images.values_list('id', flat=True))

    Product = _get_model(apps, settings.PRODUCTS_PRODUCT_MODEL, 'products', 'Product')
    if Product is not None:
        for product in Product.objects.filter(images__isnull=False):
            product.images_tmp = list(product.images.values_list('id', flat=True))

    Service = _get_model(apps, settings.PRODUCTS_SERVICE_MODEL, 'products', 'Service')
    if Service is not None:
        for service in Service.objects.filter(images__isnull=False):
            service.images_tmp = list(service.images.values_list('id', flat=True))


def fix_header_filters(apps, schema_editor):
    ctypes = _get_ctypes(apps)
    HeaderFilter = apps.get_model('creme_core', 'HeaderFilter')

    for model_name, ct in ctypes:
        for hf in HeaderFilter.objects.filter(entity_type=ct.id):
            cells = json_load(hf.json_cells)

            if _update_cells(cells, hf, model_name):
                hf.json_cells = json_dump(cells)
                hf.save()


def fix_custom_blocks(apps, schema_editor):
    ctypes = _get_ctypes(apps)
    CustomBlockConfigItem = apps.get_model('creme_core', 'CustomBlockConfigItem')

    for model_name, ct in ctypes:
        for cbci in CustomBlockConfigItem.objects.filter(content_type=ct.id):
            cells = json_load(cbci.json_cells)

            if _update_cells(cells, cbci, model_name):
                cbci.json_cells = json_dump(cells)
                cbci.save()


def fix_relation_blocks(apps, schema_editor):
    ctypes = {ct.id: model_name for model_name, ct in _get_ctypes(apps)}
    if not ctypes:
        return

    RelationBlockItem = apps.get_model('creme_core', 'RelationBlockItem')

    for rbi in RelationBlockItem.objects.filter(json_cells_map__isnull=False):
        cells_map = json_load(rbi.json_cells_map)
        save = False

        for ct_id, cells in cells_map.iteritems():
            model_name = ctypes.get(int(ct_id))

            if model_name is not None:
                save = _update_cells(cells, rbi, model_name) or save

        if save:
            rbi.json_cells_map = json_dump(cells_map)
            rbi.save()


def fix_entity_filters(apps, schema_editor):
    ctypes = _get_ctypes(apps)
    EntityFilterCondition = apps.get_model('creme_core', 'EntityFilterCondition')

    for model_name, ct in ctypes:
        for efc in EntityFilterCondition.objects.filter(filter__entity_type=ct.id,
                                                        name__startswith='images__',
                                                       ):
            name = efc.name

            if name == 'images__name':
                efc.name = 'images__title'
                efc.save()
            elif name in ('images__height', 'images__width'):
                efilter = efc.filter
                print('The EntityFilter "%s" (id="%s") use a deprecated Image field (width/height) '
                      "& so we delete it (you'll have to fix it manually)." % (
                            efilter.name, efilter.id,
                        )
                     )

                efc.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0005_v1_7__image_to_doc_1'),
    ]

    operations = [
        migrations.RunPython(replace_img_m2m),
        migrations.RunPython(fix_header_filters),
        migrations.RunPython(fix_custom_blocks),
        migrations.RunPython(fix_relation_blocks),
        migrations.RunPython(fix_entity_filters),
    ]
