# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from json import dumps as json_dump
from os import listdir, rmdir
from os.path import join, exists, isdir

from django.conf import settings
from django.db import migrations

from creme.creme_core.utils import truncate_str


EFC_FIELD = 5
NAME_LENGTH = 100
STARTSWITH = 13
MIMETYPE_PREFIX_IMG = 'image/'


def _get_ctypes(apps):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    filter_ct = ContentType.objects.filter
    ct_image = filter_ct(app_label='media_managers', model='image').first()

    doc_app_label, doc_model_name = settings.DOCUMENTS_DOCUMENT_MODEL.split('.')
    ct_doc = filter_ct(app_label=doc_app_label, model=doc_model_name.lower()).first()

    return ContentType, ct_image, ct_doc


def convert_efilters(apps, schema_editor):
    ContentType, ct_image, ct_doc = _get_ctypes(apps)

    if ct_image is None:
        return

    get_model = apps.get_model
    EntityFilterCondition = get_model('creme_core', 'EntityFilterCondition')
    filter_conditions = EntityFilterCondition.objects.filter

    filter_conditions(filter__entity_type=ct_image.id, type=EFC_FIELD, name='name').update(name='title')

    for efilter in get_model('creme_core', 'EntityFilter').objects.filter(entity_type=ct_image.id):
        conditions = filter_conditions(filter=efilter, type=EFC_FIELD, name__in=('height', 'width'))
        if conditions:
            print('The Image filter "%s" (id="%s") uses the fields "height"/"width" which are deleted ; '
                  'so this filter is probably broken (& should be manually fixed in the GUI).' % (
                        efilter.name, efilter.id,
                    )
                 )
            conditions.delete()

        conditions = filter_conditions(filter=efilter, type=EFC_FIELD, name__in=('categories', 'categories__name'))
        if conditions:
            print('The Image filter "%s" (id="%s") uses the field "categories" which has changed during the merge '
                  'with the Document model; so this filter should be manually fixed in the GUI.' % (
                        efilter.name, efilter.id,
                    )
                 )

        if efilter.use_or:
            print('The Image filter "%s" (id="%s") should be manually fixed in the GUI '
                  'if you want to filter only image Documents.' % (
                        efilter.name, efilter.id,
                    )
                 )
            efilter.name = truncate_str(efilter.name, max_length=NAME_LENGTH, suffix=' (to be fixed)')
        else:
            EntityFilterCondition.objects.create(filter=efilter,
                                                 type=EFC_FIELD, name='mime_type__name',
                                                 value=json_dump({'operator': STARTSWITH,
                                                                  'values': [MIMETYPE_PREFIX_IMG],
                                                                 }
                                                                ),
                                                )
            efilter.name = truncate_str(efilter.name, max_length=NAME_LENGTH, suffix=' (migrated)')

        efilter.entity_type = ct_doc
        efilter.save()


def convert_roles(apps, schema_editor):
    ContentType, ct_image, ct_doc = _get_ctypes(apps)

    if ct_image is None:
        return

    get_model = apps.get_model
    SetCredentials = get_model('creme_core', 'SetCredentials')

    for role in get_model('creme_core', 'UserRole').objects.all():
        save = False

        allowed_apps = [app_name for app_name in role.raw_allowed_apps.split('\n') if app_name]
        if 'media_managers' in allowed_apps:
            if 'documents' not in allowed_apps:
                print('The UserRole "%s" allows the app "media_managers" & not the app "documents", '
                      'so you should fix it manually to set the wanted behaviour.' % role.name
                     )

            role.raw_allowed_apps = '\n'.join(app_name for app_name in allowed_apps if app_name != 'media_managers')
            save = True

        admin_4_apps = [app_name for app_name in role.raw_admin_4_apps.split('\n') if app_name]
        if 'media_managers' in admin_4_apps:
            if 'documents' not in admin_4_apps:
                print('The UserRole "%s" allows the administration of the app "media_managers" & not the '
                      'app "documents", so you should fix it manually to set the wanted behaviour.' % role.name
                     )

            role.raw_admin_4_apps = '\n'.join(app_name for app_name in admin_4_apps if app_name != 'media_managers')
            save = True

        if save:
            role.save()

        ctype_ids = set(role.creatable_ctypes.values_list('id', flat=True))
        if ct_image.id in ctype_ids and ct_doc.id not in ctype_ids:
            print('The UserRole "%s" allows the creation of the model "Image" & not the '
                  'model "Document", so you should fix it manually to set the wanted behaviour.' % role.name
                 )
            role.creatable_ctypes.remove(ct_image.id)

        ctype_ids = set(role.exportable_ctypes.values_list('id', flat=True))
        if ct_image.id in ctype_ids and ct_doc.id not in ctype_ids:
            print('The UserRole "%s" allows the export of the model "Image" & not the '
                  'model "Document", so you should fix it manually to set the wanted behaviour.' % role.name
                 )
            role.exportable_ctypes.remove(ct_image.id)

        screds = SetCredentials.objects.filter(role=role, ctype=ct_image.id)
        if screds.exists():
            print('The UserRole "%s" use specific credentials for the model "Image", '
                  'so you should fix it manually to set the wanted behaviour.' % role.name
                 )
            screds.delete()


def clean_db(apps, schema_editor):
    ContentType, ct_image, ct_doc = _get_ctypes(apps)

    if ct_image is None:
        return

    get_model = apps.get_model
    get_model('creme_core', 'ButtonMenuItem').objects.filter(content_type=ct_image.id).delete()
    get_model('creme_core', 'BlockDetailviewLocation').objects.filter(content_type=ct_image.id).delete()
    get_model('creme_core', 'BlockPortalLocation').objects.filter(app_name='media_managers').delete()
    get_model('creme_core', 'PreferedMenuItem').objects.filter(url__startswith='/media_managers/').delete()

    get_model('creme_core', 'FieldsConfig').objects.filter(content_type=ct_image.id).delete()
    get_model('creme_core', 'SearchConfigItem').objects.filter(content_type=ct_image.id).delete()

    get_model('creme_core', 'HeaderFilter').objects.filter(entity_type=ct_image.id).delete()

    # --------------------
    ct_image.delete()
    ContentType.objects.filter(app_label='media_managers', model='mediacategory').delete()


def clean_fs(apps, schema_editor):
    files_path = join(settings.MEDIA_ROOT, 'upload', 'images')

    if exists(files_path) and isdir(files_path):
        if listdir(files_path):
            print(u'The directory "%s" contains some files ; the useful ones has been copied to "%s". '
                  u'If no other program uses these files (eg: a web server which serves them statically), '
                  u'you can delete this directory (you should check that your install is OK).' % (
                        files_path,
                        join(settings.MEDIA_ROOT, 'upload', 'documents'),
                    )
                 )
        else:
            rmdir(files_path)


class Migration(migrations.Migration):
    dependencies = [
        ('media_managers', '0002_v1_7__delete_all_models'),
    ]

    operations = [
        migrations.RunPython(convert_efilters),
        migrations.RunPython(convert_roles),
        migrations.RunPython(clean_db),
        migrations.RunPython(clean_fs),
    ]
