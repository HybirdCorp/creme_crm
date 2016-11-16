# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import join, basename, splitext

from django.conf import settings
from django.db import migrations
from django.utils.translation import activate as activate_trans, ugettext as _

from creme.creme_core.utils.file_handling import FileCreator


UUID_DOC_CAT_IMG_PRODUCT = 'a6624a65-7f02-4952-8cd8-02449e5b507b'
UUID_DOC_CAT_IMG_ORGA    = 'b1486e1c-633a-4849-95bc-376119135dcd'
UUID_DOC_CAT_IMG_CONTACT = 'fad633b9-a270-4708-917e-1d73b2514f06'


def replace_images_by_docs(apps, schema_editor):
    if settings.DOCUMENTS_FOLDER_MODEL != 'documents.Folder':
        return

    if settings.DOCUMENTS_DOCUMENT_MODEL != 'documents.Document':
        return

    if settings.AUTH_USER_MODEL != 'creme_core.CremeUser':
        return

    get_model = apps.get_model
    Image = get_model('media_managers', 'Image')

    if not Image.objects.exists():
        return

    activate_trans(settings.LANGUAGE_CODE)

    ContentType = get_model('contenttypes', 'ContentType')

    # ----------------------
    user_qs = get_model('creme_core', 'CremeUser').objects.order_by('id')
    user = user_qs.filter(is_superuser=True, is_staff=False).first() or \
           user_qs.filter(is_superuser=True).first() or \
           user_qs[0]

    # ----------------------
    folder_title = _(u'Images')
    folder = get_model('documents', 'Folder') \
                .objects \
                .get_or_create(title=folder_title,
                               parent_folder=None,
                               category=None,
                               defaults={
                                   'user': user,
                                   'entity_type': ContentType.objects.get(app_label='documents',
                                                                          model='folder',
                                                                         ),
                                   'header_filter_search_field': folder_title,
                               }
                              )[0]

    # ----------------------
    create_doc_cat = get_model('documents', 'DocumentCategory').objects.get_or_create
    category_conversion = {
        1: create_doc_cat(uuid=UUID_DOC_CAT_IMG_PRODUCT,
                          defaults={'name': _(u'Product image'),  # TODO: name could have been edited....
                                    'is_custom': False,
                                   }
                         )[0],
        2: create_doc_cat(uuid=UUID_DOC_CAT_IMG_ORGA,
                          defaults={'name': _(u'Organisation logo'),
                                    'is_custom': False,
                                   }
                         )[0],
        3: create_doc_cat(uuid=UUID_DOC_CAT_IMG_CONTACT,
                          defaults={'name': _(u'Contact photograph'),
                                    'is_custom': False,
                                   }
                         )[0],
    }

    category_conversion.update(
        (img_cat.id,
         create_doc_cat(name=img_cat.name,
                        defaults={'is_custom': img_cat.is_custom},
                       )[0]
        ) for img_cat in get_model('media_managers',
                                   'MediaCategory',
                                  ).objects
                                   .exclude(pk__in=(1, 2, 3))
                                   .exclude(Image_media_category_set__isnull=True)
    )

    # ----------------------
    relative_dir_path = join('upload', 'documents')
    doc_dir_path = join(settings.MEDIA_ROOT, relative_dir_path)

    # NB: 1 is for the final '/'
    #     The storage uses '/' even on Windows.
    dir_path_length = 1 + len('/'.join(relative_dir_path))

    # 500 is for: filedata = FileField(_(u'File'), max_length=500, ...)
    max_length = 500 - dir_path_length

    if max_length <= 0:
        raise ValueError('The max length of Document.filedata is too small.')

    get_or_create_doc = get_model('documents', 'Document').objects.get_or_create
    ct_doc = ContentType.objects.get(app_label='documents', model='document')

    for img in Image.objects.all():
        final_name = basename(unicode(img.image))

        # Try to remove {{id}}_ prefix set by ImageForm
        prefix, _sep, tail = final_name.partition('_')
        if tail and prefix == str(img.id):
            final_name = tail

        final_path = FileCreator(dir_path=doc_dir_path, name=final_name, max_length=max_length).create()
        title = img.name or splitext(final_name)[0]
        doc = get_or_create_doc(id=img.id,
                                defaults={
                                    'user': img.user,
                                    'entity_type': ct_doc,
                                    'header_filter_search_field': u'%s - %s' % (folder.title, title),
                                    'is_deleted': img.is_deleted,

                                    'title': title,
                                    'description': img.description or '',
                                    'folder': folder,
                                    'filedata': join(relative_dir_path, basename(final_path)),
                                    'filedata_tmp': img.image,
                                }
                               )[0]

        doc.categories = [category_conversion[mcat_id]
                            for mcat_id in img.categories.values_list('id', flat=True)
                         ]

    # -------------------------
    ct_img = ContentType.objects.get(app_label='media_managers', model='image')
    # NB: passing ContentTypes objects odes not work...
    get_model('creme_core', 'HistoryLine').objects.filter(entity_ctype=ct_img.id)\
                                                  .update(entity_ctype=ct_doc.id)
    get_model('creme_core', 'CustomField').objects.filter(content_type=ct_img.id)\
                                                  .update(content_type=ct_doc.id)


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes',   '0002_remove_content_type_name'),
        ('media_managers', '0001_initial'),
        ('documents',      '0006_v1_7__image_to_doc_1'),
    ]

    operations = [
        migrations.RunPython(replace_images_by_docs),
    ]
