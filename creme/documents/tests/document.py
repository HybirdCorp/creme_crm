 # -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.core.serializers.json import DjangoJSONEncoder as JSONEncoder
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from creme.creme_core.models import CremeEntity, RelationType, HeaderFilter, SetCredentials
    from creme.creme_core.auth.entity_credentials import EntityCredentials

    from creme.persons.models import Organisation

    from .base import _DocumentsTestCase
    from ..models import Folder, FolderCategory, Document
    from ..constants import REL_SUB_RELATED_2_DOC
    from ..utils import get_csv_folder_or_create
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('DocumentTestCase', 'DocumentQuickFormTestCase', 'CSVDocumentQuickWidgetTestCase')


class DocumentTestCase(_DocumentsTestCase):
    def _buid_addrelated_url(self, entity):
        return '/documents/document/add_related/%s' % entity.id

    def test_populate(self):
        self.get_object_or_fail(RelationType, pk=REL_SUB_RELATED_2_DOC)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Document)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Folder)).exists())

        self.assertTrue(Folder.objects.exists())
        self.assertTrue(FolderCategory.objects.exists())

    def test_portal(self):
        self.login()
        self.assertGET200('/documents/')

    def test_createview01(self):
        self.login()

        self.assertFalse(Document.objects.exists())

        url = self.ADD_DOC_URL
        self.assertGET200(url)

        ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
        self.assertTrue(ALLOWED_EXTENSIONS)
        ext = ALLOWED_EXTENSIONS[0]

        title = 'Test doc'
        description = 'Test description'
        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        file_obj, file_name = self._build_filedata(content, suffix='.%s' % ext)
        folder   = Folder.objects.all()[0]
        response = self._create_doc(title, file_obj, folder, description)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        self.assertRedirects(response, '/documents/document/%s' % doc.id)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s' % file_name, filedata.name)
        filedata.open()
        self.assertEqual([content], filedata.readlines())

        #Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview02(self):
        "Unallowed extension"
        self.login()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        file_obj, file_name = self._build_filedata('Content', suffix='.%s' % ext)
        self._create_doc(title, file_obj)

        doc = self.get_object_or_fail(Document, title=title)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s.txt' % file_name, filedata.name)

        #Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview03(self):
        "Double extension (bugfix)"
        self.login()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        file_obj, file_name = self._build_filedata('Content', suffix='.old.%s' % ext)
        self._create_doc(title, file_obj)

        doc = self.get_object_or_fail(Document, title=title)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s.txt' % file_name, filedata.name)

        #Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

    def test_createview04(self):
        "No extension"
        self.login()

        title = 'My doc'
        file_obj, file_name = self._build_filedata('Content', suffix='')
        self._create_doc(title, file_obj)
        doc = self.get_object_or_fail(Document, title=title)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s.txt' % file_name, filedata.name)

        #Download
        response = self.assertGET200('/download_file/%s' % doc.filedata)
        self.assertEqual('txt', response['Content-Type']) # 'text/plain' ??
        self.assertEqual('attachment; filename=%s.txt' % file_name,
                         response['Content-Disposition']
                        )

    def test_editview(self):
        self.login()

        title       = 'Test doc'
        description = 'Test description'
        content     = 'Yes I am the content (DocumentTestCase.test_editview)'
        self._create_doc(title, self._build_filedata(content)[0], description=description)

        doc = self.get_object_or_fail(Document, title=title)

        url = '/documents/document/edit/%s' % doc.id
        self.assertGET200(url)

        title       = title.upper()
        description = description.upper()
        content     = content.upper()
        folder      = Folder.objects.create(title=u'Test folder', parent_folder=None,
                                            category=FolderCategory.objects.all()[0],
                                            user=self.user,
                                           )

        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'folder':       folder.id,
                                         }
                                   )
        self.assertNoFormError(response)

        doc = self.refresh(doc)
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        self.assertRedirects(response, doc.get_absolute_url())

    def test_add_related_document01(self):
        self.login()

        folders = Folder.objects.all()
        self.assertEqual(1, len(folders))
        root_folder = folders[0]

        entity = CremeEntity.objects.create(user=self.user)

        url = self._buid_addrelated_url(entity)
        self.assertGET200(url)

        def post(title):
            response = self.client.post(url, follow=True,
                                        data={'user':         self.user.pk,
                                              'title':        title,
                                              'description':  'Test description',
                                              'filedata':     self._build_filedata('Yes I am the content '
                                                                                   '(DocumentTestCase.test_add_related_document01)'
                                                                                  )[0],
                                             }
                                    )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Document, title=title)

        doc1 = post('Related doc')
        self.assertRelationCount(1, entity, REL_SUB_RELATED_2_DOC, doc1)

        entity_folder = doc1.folder
        self.assertIsNotNone(entity_folder)
        self.assertEqual(u'%s_%s' % (entity.id, unicode(entity)), entity_folder.title)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(unicode(CremeEntity._meta.verbose_name), ct_folder.title)
        self.assertEqual(root_folder, ct_folder.parent_folder)

        doc2 = post('Related doc #2')
        entity_folder2 = doc2.folder
        self.assertEqual(entity_folder, entity_folder2)
        self.assertEqual(ct_folder,     entity_folder2.parent_folder)

    def test_add_related_document02(self):
        "Creation credentials"
        self.login(is_superuser=False, allowed_apps=['documents', 'persons'])

        entity = CremeEntity.objects.create(user=self.user)
        #self.assertGET(302, self._buid_addrelated_url(entity))
        self.assertGET403(self._buid_addrelated_url(entity))

    def test_add_related_document03(self):
        "Link credentials"
        self.login(is_superuser=False, allowed_apps=['documents', 'persons'],
                   creatable_models=[Document]
                  )

        create_sc = partial(SetCredentials.objects.create, role=self.role,
                            set_type=SetCredentials.ESET_OWN,
                           )
        create_sc(value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK, #not EntityCredentials.LINK
                 )

        user = self.user
        orga = Organisation.objects.create(user=user, name='NERV')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._buid_addrelated_url(orga)
        self.assertGET403(url)

        get_ct = ContentType.objects.get_for_model
        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Organisation))
        self.assertGET403(url)

        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Document))
        self.assertGET200(url)

        response = self.assertPOST200(url, follow=True,
                                      data={'user':         self.other_user.pk,
                                            'title':        'Title',
                                            'description':  'Test description',
                                            'filedata':     self._build_filedata('Yes I am the content '
                                                                                 '(DocumentTestCase.test_add_related_document03)'
                                                                                )[0],
                                           }
                                     )
        self.assertFormError(response, 'form', 'user',
                             [_(u'You are not allowed to link with the «%s» of this user.') % _(u'Documents')]
                            )

    def test_add_related_document04(self):
        "View credentials"
        self.login(is_superuser=False, allowed_apps=['documents', 'persons'],
                   creatable_models=[Document],
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK, #not EntityCredentials.VIEW
                                      set_type=SetCredentials.ESET_ALL
                                     )

        #entity = CremeEntity.objects.create(user=self.other_user)
        orga = Organisation.objects.create(user=self.other_user, name='NERV')
        self.assertTrue(self.user.has_perm_to_link(orga))
        self.assertFalse(self.user.has_perm_to_view(orga))
        self.assertGET403(self._buid_addrelated_url(orga))

    def test_add_related_document05(self):
        "The Folder containing all the Documents related to the entity has a too long name."
        self.login()

        MAX_LEN = 100
        self.assertEqual(MAX_LEN, Folder._meta.get_field('title').max_length)

        with self.assertNoException():
            entity = Organisation.objects.create(user=self.user, name='A' * MAX_LEN)

        self.assertEqual(100, len(unicode(entity)))

        title    = 'Related doc'
        response = self.client.post(self._buid_addrelated_url(entity),
                                    follow=True,
                                    data={'user':        self.user.pk,
                                          'title':       title,
                                          'description': 'Test description',
                                          'filedata':    self._build_filedata('Yes I am the content '
                                                                              '(DocumentTestCase.test_add_related_document05)'
                                                                             )[0],
                                         }
                                   )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)
        entity_folder = doc.folder
        self.assertIsNotNone(entity_folder)

        title = entity_folder.title
        self.assertEqual(100, len(title))
        self.assertTrue(title.startswith(u'%s_AAAAAAA' % entity.id))
        self.assertTrue(title.endswith(u'…'))

    def test_listview(self):
        self.login()

        def create_doc(title):
            self._create_doc(title, description='Test description',
                             file_obj=self._build_filedata('%s : Content (DocumentTestCase.test_listview)' % title)[0],
                            )

            return self.get_object_or_fail(Document, title=title)

        doc1 = create_doc('Test doc #1')
        doc2 = create_doc('Test doc #2')

        response = self.assertGET200('/documents/documents')

        with self.assertNoException():
            docs = response.context['entities'].object_list

        self.assertIn(doc1, docs)
        self.assertIn(doc2, docs)

    def test_delete_category(self):
        "Set to null"
        self.login()

        cat = FolderCategory.objects.create(name='Manga')
        folder = Folder.objects.create(user=self.user, title='One piece', category=cat)

        self.assertPOST200('/creme_config/documents/category/delete', data={'id': cat.pk})
        self.assertFalse(FolderCategory.objects.filter(pk=cat.pk).exists())

        folder = self.get_object_or_fail(Folder, pk=folder.pk)
        self.assertIsNone(folder.category)

    #TODO (block not yet injected in all apps)
    #def test_orga_block(self):
        #self.login()
        #orga = Organisation.objects.create(user=self.user, name='NERV')
        #response = self.assertGET200(orga.get_absolute_url())
        #self.assertTemplateUsed(response, 'documents/templatetags/block_linked_docs.html')

    #TODO complete


class DocumentQuickFormTestCase(_DocumentsTestCase):
    def quickform_data(self, count):
        return {'form-INITIAL_FORMS': '0',
                'form-MAX_NUM_FORMS': '',
                'form-TOTAL_FORMS':   '%s' % count,
               }

    def quickform_data_append(self, data, id, user='', filedata='', folder=''):
        return data.update({'form-%d-user' % id:     user,
                            'form-%d-filedata' % id: filedata,
                            'form-%d-folder' % id:   folder,
                           }
                          )

    def test_add(self):
        self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = '/creme_core/quickforms/%s/%d' % (ContentType.objects.get_for_model(Document).pk, 1)
        self.assertGET200(url)

        content = 'Yes I am the content (DocumentQuickFormTestCase.test_add)'
        file_obj, file_name = self._build_filedata(content)
        folder = Folder.objects.all()[0]

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, user=self.user.pk, filedata=file_obj, folder=folder.pk)

        self.assertNoFormError(self.client.post(url, follow=True, data=data))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual('upload/documents/%s' % file_name, doc.filedata.name)
        self.assertIsNone(doc.description)
        self.assertEqual(folder, doc.folder)

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())


class CSVDocumentQuickWidgetTestCase(_DocumentsTestCase):
    def test_add_from_widget(self):
        self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = '/documents/quickforms/from_widget/document/csv/add/%d' % 1
        self.assertGET200(url)

        content = 'Content (CSVDocumentQuickWidgetTestCase.test_add_from_widget)'
        file_obj, file_name = self._build_filedata(content)
        response = self.client.post(url, follow=True,
                                    data={'user':     self.user.pk,
                                          'filedata': file_obj,
                                         }
                                   )
        self.assertNoFormError(response)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        folder = get_csv_folder_or_create(self.user)
        self.assertEqual('upload/documents/%s' % file_name, doc.filedata.name)
        self.assertIsNone(doc.description)
        self.assertEqual(folder, doc.folder)

        self.assertEqual(u'<json>%s</json>' % JSONEncoder().encode({
                                'added': [[doc.id, unicode(doc)]],
                                'value': doc.id,
                            }),
                         response.content
                        )

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())
