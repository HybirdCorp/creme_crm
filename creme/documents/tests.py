# -*- coding: utf-8 -*-

try:
    from os import remove as delete_file
    from os.path import basename
    from tempfile import NamedTemporaryFile

    from django.core.serializers.json import DjangoJSONEncoder as JSONEncoder
    from django.utils.translation import ugettext
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import User

    from creme_core.models import CremeEntity, RelationType, Relation, HeaderFilter, HistoryLine, SetCredentials
    from creme_core.tests.base import CremeTestCase

    from persons.models import Organisation

    from documents.models import Folder, FolderCategory, Document
    from documents.constants import *
    from documents.utils import get_csv_folder_or_create
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class _DocumentsTestCase(CremeTestCase):
    ADD_DOC_URL = '/documents/document/add'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'documents')

    def setUp(self):
        self._tmp_filepaths = []

    def tearDown(self):
        for path in self._tmp_filepaths:
            delete_file(path)

    def _build_filedata(self, content_str, suffix='.txt'):
        tmpfile = NamedTemporaryFile(suffix=suffix, delete=False)
        tmpfile.write(content_str)
        tmpfile.flush()

        #we close and reopen in order to have a file with the right name (so we must specify delete=False)
        tmpfile.close()

        name = tmpfile.name
        self._tmp_filepaths.append(name)

        return open(name, 'rb'), basename(name)

    def _create_doc(self, title, file_obj, folder=None, description=None):
        folder = folder or Folder.objects.all()[0]
        data = {'user':     self.user.pk,
                'title':    title,
                'filedata': file_obj,
                'folder':   folder.id,
               }

        if description is not None:
            data['description'] = description

        response = self.client.post(self.ADD_DOC_URL, follow=True, data=data)
        self.assertNoFormError(response)

        return response


class DocumentTestCase(_DocumentsTestCase):
    def _buid_addrelated_url(self, entity):
        return '/documents/document/add_related/%s' % entity.id

    def test_populate(self):
        self.assertTrue(RelationType.objects.filter(pk=REL_SUB_RELATED_2_DOC).exists())

        get_ct = ContentType.objects.get_for_model
        self.assertTrue(HeaderFilter.objects.filter(entity_type=get_ct(Document)).exists())

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
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        filedata = doc.filedata
        self.assertEqual('upload/documents/%s' % file_name, filedata.name)
        filedata.open()
        self.assertEqual([content], filedata.readlines())

        #Download
        response = self.client.get('/download_file/%s' % doc.filedata)
        self.assertEqual(200, response.status_code)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

        filedata.delete(filedata) #clean #TODO: in tearDown()...

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
        response = self.client.get('/download_file/%s' % doc.filedata)
        self.assertEqual(200, response.status_code)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

        filedata.delete(filedata) #clean

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
        response = self.client.get('/download_file/%s' % doc.filedata)
        self.assertEqual(200, response.status_code)
        self.assertEqual(ext, response['Content-Type'])
        self.assertEqual('attachment; filename=%s' % file_name,
                         response['Content-Disposition']
                        )

        filedata.delete(filedata) #clean

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
        response = self.client.get('/download_file/%s' % doc.filedata)
        self.assertEqual(200, response.status_code)
        self.assertEqual('txt', response['Content-Type']) # 'text/plain' ??
        self.assertEqual('attachment; filename=%s.txt' % file_name,
                         response['Content-Disposition']
                        )

        filedata.delete(filedata) #clean

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
        file_to_delete = doc.filedata

        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'folder':       folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        doc = self.refresh(doc)
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        file_to_delete.delete(file_to_delete)#clean

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

        for doc in (doc1, doc2):
            doc.filedata.delete(doc.filedata) #clean

    def test_add_related_document02(self): #creation credentials
        self.login(is_superuser=False, allowed_apps=['documents', 'persons'])

        entity = CremeEntity.objects.create(user=self.user)
        self.assertEqual(302, self.client.get(self._buid_addrelated_url(entity)).status_code)

    def test_add_related_document03(self): #link credentials
        self.login(is_superuser=False, allowed_apps=['documents', 'persons'], creatable_models=[Document])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | \
                                            SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_UNLINK, #not CRED_LINK
                                      set_type=SetCredentials.ESET_ALL
                                     )

        entity = CremeEntity.objects.create(user=self.other_user)
        orga = Organisation.objects.create(user=self.other_user, name='NERV')
        self.assertTrue(orga.can_view(self.user))
        self.assertFalse(orga.can_link(self.user))
        self.assertEqual(403, self.client.get(self._buid_addrelated_url(orga)).status_code)

    def test_add_related_document04(self): #view credentials
        self.login(is_superuser=False, allowed_apps=['documents', 'persons'], creatable_models=[Document])

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK   | \
                                            SetCredentials.CRED_UNLINK, #not SetCredentials.CRED_VIEW
                                      set_type=SetCredentials.ESET_ALL
                                     )

        entity = CremeEntity.objects.create(user=self.other_user)
        orga = Organisation.objects.create(user=self.other_user, name='NERV')
        self.assertTrue(orga.can_link(self.user))
        self.assertFalse(orga.can_view(self.user))
        self.assertEqual(403, self.client.get(self._buid_addrelated_url(orga)).status_code)

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

        doc.filedata.delete(doc.filedata) #clean

    def test_listview(self):
        self.login()

        def create_doc(title):
            self._create_doc(title, description='Test description',
                             file_obj=self._build_filedata('%s : Content (DocumentTestCase.test_listview)' % title)[0],
                            )

            return self.get_object_or_fail(Document, title=title)

        doc1 = create_doc('Test doc #1')
        doc2 = create_doc('Test doc #2')

        response = self.client.get('/documents/documents')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            docs_page = response.context['entities']

        self.assertIn(doc1, docs_page.object_list)
        self.assertIn(doc2, docs_page.object_list)

        #clean
        doc1.filedata.delete(doc1.filedata)
        doc2.filedata.delete(doc2.filedata)

    def test_delete_category(self):
        "Set to null"
        self.login()

        cat = FolderCategory.objects.create(name='Manga')
        folder = Folder.objects.create(user=self.user, title='One piece', category=cat)

        self.assertPOST200('/creme_config/documents/category/delete', data={'id': cat.pk})
        self.assertFalse(FolderCategory.objects.filter(pk=cat.pk).exists())

        folder = self.get_object_or_fail(Folder, pk=folder.pk)
        self.assertIsNone(folder.category)

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

        filedata.delete(filedata) #clean


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

        filedata.delete(filedata) #clean


class FolderTestCase(_DocumentsTestCase):
    def setUp(self):
        super(FolderTestCase, self).setUp()
        self.login()

    def test_createview(self):
        url = '/documents/folder/add'
        self.assertGET200(url)

        title = 'Test folder'
        self.assertFalse(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        parent      = Folder.objects.all()[0]
        category    = FolderCategory.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':          self.user.pk,
                                          'title':         title,
                                          'description':   description,
                                          'parent_folder': parent.id,
                                          'category':      category.id,
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            folder = Folder.objects.get(title=title)

        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)
        self.assertEqual(category,    folder.category)

    def test_editview(self):
        title = u'Test folder'
        description = 'Test description'
        category = FolderCategory.objects.all()[0]
        folder = Folder.objects.create(title=title,
                                       description=description,
                                       parent_folder=None,
                                       category=category,
                                       user=self.user,
                                      )

        url = '/documents/folder/edit/%s' % folder.id
        self.assertGET200(url)

        title       += u' edited'
        description = description.upper()
        parent      = Folder.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':          self.user.pk,
                                          'title':         title,
                                          'description':   description,
                                          'parent_folder': parent.id,
                                          'category':      category.id,
                                         }
                                   )
        self.assertNoFormError(response)

        folder = self.refresh(folder)
        self.assertEqual(title,       folder.title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)
        self.assertEqual(category,    folder.category)

    def test_listview(self):
        user = self.user
        category = FolderCategory.objects.all()[0]

        create_folder = Folder.objects.create
        folder1 = create_folder(user=user, title='PDF',
                                description='Contains PDF files',
                                parent_folder=None, category=category
                               )
        folder2 = create_folder(user=user, title='SVG',
                                description='Contains SVG files',
                                parent_folder=None, category=category
                               )

        response = self.client.get('/documents/folders')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            folders = response.context['entities'].object_list

        self.assertIn(folder1, folders)
        self.assertIn(folder2, folders)

    def test_folder_clone01(self):
        title = 'folder'
        folder = Folder.objects.create(user=self.user, title=title, description="d")

        stack = [folder]
        stack_append = stack.append

        for i in xrange(100):
            clone = folder.clone()
            self.assertNotEqual(stack[-1].title, clone.title)
            stack_append(clone)

    def test_deleteview01(self):
        "No doc inside"
        folder = Folder.objects.create(user=self.user, title='PDF',
                                       description='Contains PDF files',
                                       parent_folder=None,
                                       category=FolderCategory.objects.all()[0],
                                      )

        response = self.client.post('/creme_core/entity/delete/%s' % folder.pk, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertFalse(Folder.objects.filter(pk=folder.pk).exists())
        self.assertRedirects(response, '/documents/folders')

    def test_deleteview02(self):
        "A doc inside protect from deletion"
        folder = Folder.objects.create(user=self.user, title='PDF',
                                       description='Contains PDF files',
                                       parent_folder=None,
                                       category=FolderCategory.objects.all()[0]
                                      )

        title = 'Boring title'
        self._create_doc(title, folder=folder, description='Boring description too',
                         file_obj=self._build_filedata('Content (FolderTestCase.test_deleteview02)')[0],
                        )

        doc = self.get_object_or_fail(Document, title=title)
        self.assertEqual(folder, doc.folder)

        self.assertPOST200('/creme_core/entity/delete/%s' % folder.pk)
        self.get_object_or_fail(Folder, pk=folder.pk)

        doc.filedata.delete(doc.filedata) #clean
