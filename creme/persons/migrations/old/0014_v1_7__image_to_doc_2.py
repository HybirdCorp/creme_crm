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
            img_field = concrete_model._meta.get_field('image')
        except FieldDoesNotExist:
            print('It seems that your custom model which replaces <%s> has not ForeignKey to Image.' % model_name)
        else:
            if isinstance(img_field, models.ForeignKey) and \
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

    contact_info = _get_ct(settings.PERSONS_CONTACT_MODEL, 'persons', 'Contact')
    if contact_info is not None:
        ctypes.append(contact_info)

    orga_info = _get_ct(settings.PERSONS_ORGANISATION_MODEL, 'persons', 'Organisation')
    if orga_info is not None:
        ctypes.append(orga_info)

    return ctypes


def _update_cells(cells, instance, related_model_name):
    save = False

    for cell in cells:
        if cell['type'] != 'regular_field':
            continue

        fname = cell['value']
        if fname == 'image__name':
            cell['value'] = 'image__title'
            save = True
        elif fname == 'image__image':
            cell['value'] = 'image__filedata'
            save = True
        elif fname in ('image__height', 'image__width'):
            print('The %s id="%s" (for <%s>) use a removed field Image.height/width.' % (
                        instance.__class__.__name__,
                        instance.id,
                        related_model_name,
                    )
                 )

    return save


def replace_img_fks(apps, schema_editor):
    Contact = _get_model(apps, settings.PERSONS_CONTACT_MODEL, 'persons', 'Contact')
    if Contact is not None:
        for contact in Contact.objects.exclude(image=None):
            contact.image_tmp_id = contact.image_id
            contact.save()

    Organisation = _get_model(apps, settings.PERSONS_ORGANISATION_MODEL, 'persons', 'Organisation')
    if Organisation is not None:
        for orga in Organisation.objects.exclude(image=None):
            orga.image_tmp_id = orga.image_id
            orga.save()


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

    for rbi in RelationBlockItem.objects.all():
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
                                                        name__startswith='image__',
                                                       ):
            name = efc.name

            if name == 'image__name':
                efc.name = 'image__title'
                efc.save()
            elif name in ('image__height', 'image__width'):
                efilter = efc.filter
                print('The EntityFilter "%s" (id="%s") use a deprecated Image field (width/height) '
                      "& so we delete it (you'll have to fix it manually)." % (
                            efilter.name, efilter.id,
                        )
                     )

                efc.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('persons', '0013_v1_7__image_to_doc_1'),
    ]

    operations = [
         migrations.RunPython(replace_img_fks),
         migrations.RunPython(fix_header_filters),
         migrations.RunPython(fix_custom_blocks),
         migrations.RunPython(fix_relation_blocks),
         migrations.RunPython(fix_entity_filters),
    ]
