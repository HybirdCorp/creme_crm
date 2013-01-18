# -*- coding: utf-8 -*-

try:
    from tempfile import NamedTemporaryFile

    from django.core.serializers.json import DjangoJSONEncoder as JSONEncoder
    from django.utils.translation import ugettext
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import User

    from creme_core.models import CremeEntity, RelationType, Relation, HeaderFilter, HistoryLine, SetCredentials
    from creme_core.tests.base import CremeTestCase

    from persons.models import Organisation

    from documents.models import *
    from documents.constants import *
    from documents.utils import get_csv_folder_or_create
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class _DocumentsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'documents')

    def _build_filedata(self, content_str):
        tmpfile = NamedTemporaryFile()
        tmpfile.write(content_str)
        tmpfile.flush()

        filedata = tmpfile.file
        filedata.seek(0)

        return tmpfile


class DocumentTestCase(_DocumentsTestCase):
    def test_populate(self):
        self.assertTrue(RelationType.objects.filter(pk=REL_SUB_RELATED_2_DOC).exists())

        get_ct = ContentType.objects.get_for_model
        self.assertTrue(HeaderFilter.objects.filter(entity_type=get_ct(Document)).exists())

        self.assertTrue(Folder.objects.exists())
        self.assertTrue(FolderCategory.objects.exists())

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/documents/').status_code)

    def test_createview(self):
        self.login()

        self.assertFalse(Document.objects.exists())

        url = '/documents/document/add'
        self.assertEqual(200, self.client.get(url).status_code)

        title       = 'Test doc'
        description = 'Test description'
        content     = 'Yes I am the content (DocumentTestCase.test_createview)'
        filedata    = self._build_filedata(content)
        folder      = Folder.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  description,
                                          'filedata':     filedata.file,
                                          'folder':       folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.folder)

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())

        filedata.delete(filedata) #clean

    def test_editview(self):
        self.login()

        title       = 'Test doc'
        description = 'Test description'
        content     = 'Yes I am the content (DocumentTestCase.test_editview)'
        filedata    = self._build_filedata(content)
        folder      = Folder.objects.all()[0]
        self.client.post('/documents/document/add',
                         data={'user':         self.user.pk,
                               'title':        title,
                               'description':  description,
                               'filedata':     filedata.file,
                               'folder':       folder.id,
                              }
                        )

        with self.assertNoException():
            doc = Document.objects.all()[0]

        url = '/documents/document/edit/%s' % doc.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)
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

        url = '/documents/document/add_related/%s' % entity.id
        self.assertEqual(200, self.client.get(url).status_code)

        def post(title):
            filedata = self._build_filedata('Yes I am the content (DocumentTestCase.test_add_related_document)')
            response = self.client.post(url, follow=True,
                                        data={'user':         self.user.pk,
                                              'title':        title,
                                              'description':  'Test description',
                                              'filedata':     filedata.file,
                                             }
                                    )
            self.assertNoFormError(response)
            self.assertEqual(200, response.status_code)

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
        self.assertEqual(302, self.client.get('/documents/document/add_related/%s' % entity.id).status_code)

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
        self.assertEqual(403, self.client.get('/documents/document/add_related/%s' % orga.id).status_code)

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
        self.assertEqual(403, self.client.get('/documents/document/add_related/%s' % orga.id).status_code)

    def test_add_related_document05(self):
        "The Folder containing all the Documents related to the entity has a too long name."
        self.login()

        MAX_LEN = 100
        self.assertEqual(MAX_LEN, Folder._meta.get_field('title').max_length)

        with self.assertNoException():
            entity = Organisation.objects.create(user=self.user, name='A' * MAX_LEN)

        self.assertEqual(100, len(unicode(entity)))

        title    = 'Related doc'
        filedata = self._build_filedata('Yes I am the content (DocumentTestCase.test_add_related_document)')
        response = self.client.post('/documents/document/add_related/%s' % entity.id,
                                    follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  'Test description',
                                          'filedata':     filedata.file,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

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
            filedata = self._build_filedata('%s : Yes I am the content (DocumentTestCase.test_listview)' % title)
            self.client.post('/documents/document/add',
                            data={'user':         self.user.pk,
                                'title':        title,
                                'description':  'Test description',
                                'filedata':     filedata.file,
                                'folder':       Folder.objects.values_list('id', flat=True),
                                }
                            )

            return self.get_object_or_fail(Document, title=title)

        doc1 = create_doc('Test doc #1')
        doc2 = create_doc('Test doc #2')

        response = self.client.get('/documents/documents')
        self.assertEqual(response.status_code, 200)

        with self.assertNoException():
            docs_page = response.context['entities']

        self.assertIn(doc1, docs_page.object_list)
        self.assertIn(doc2, docs_page.object_list)

        #clean
        doc1.filedata.delete(doc1.filedata)
        doc2.filedata.delete(doc2.filedata)

    def test_delete_category(self): #set to null
        self.login()

        cat = FolderCategory.objects.create(name='Manga')
        folder = Folder.objects.create(user=self.user, title='One piece', category=cat)

        response = self.client.post('/creme_config/documents/category/delete', data={'id': cat.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(FolderCategory.objects.filter(pk=cat.pk).exists())

        folder = self.get_object_or_fail(Folder, pk=folder.pk)
        self.assertIsNone(folder.category)

    #TODO complete


class DocumentQuickFormTestCase(_DocumentsTestCase):
    def quickform_data(self, count):
        return {
                'form-INITIAL_FORMS': '0',
                'form-MAX_NUM_FORMS': '',
                'form-TOTAL_FORMS':   '%s' % count,
               }

    def quickform_data_append(self, data, id, user='', filedata='', folder=''):
        return data.update({
                 'form-%d-user' % id:        user,
                 'form-%d-filedata' % id:    filedata,
                 'form-%d-folder' % id:   folder,
               })

    def test_add(self):
        self.login()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = '/creme_core/quickforms/%s/%d' % (ContentType.objects.get_for_model(Document).pk, 1)
        self.assertEqual(200, self.client.get(url).status_code)

        content     = 'Yes I am the content (DocumentQuickFormTestCase.test_add)'
        filedata    = self._build_filedata(content)
        folder      = Folder.objects.all()[0]

        data = self.quickform_data(1)
        self.quickform_data_append(data, 0, user=self.user.pk, filedata=filedata.file, folder=folder.pk)

        response = self.client.post(url, follow=True, data=data)

        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]

        self.assertTrue(doc.filedata.name.endswith('fdopen.txt'));
        self.assertIsNone(doc.description)
        self.assertEqual(folder,    doc.folder)

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
        self.assertEqual(200, self.client.get(url).status_code)

        content     = 'Yes I am the content (CSVDocumentQuickWidgetTestCase.test_add_from_widget)'
        filedata    = self._build_filedata(content)
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'filedata':     filedata.file,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]

        folder = get_csv_folder_or_create(self.user)

        self.assertTrue(doc.filedata.name.endswith('fdopen.txt'));
        self.assertIsNone(doc.description)
        self.assertEqual(folder,    doc.folder)

        self.assertEqual(u"""<json>%s</json>""" % JSONEncoder().encode({
                            "added":[[doc.id, unicode(doc)]], 
                            "value":doc.id
                         }),
                         response.content)

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())

        filedata.delete(filedata) #clean


class FolderTestCase(_DocumentsTestCase):
    def setUp(self):
        self.login()

    def test_createview(self):
        url = '/documents/folder/add'
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

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
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)

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
        self.assertEqual(response.status_code, 200)

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

    def test_deleteview01(self): #no doc inside
        folder = Folder.objects.create(user=self.user, title='PDF',
                                       description='Contains PDF files',
                                       parent_folder=None,
                                       category=FolderCategory.objects.all()[0]
                                      )

        response = self.client.post('/creme_core/entity/delete/%s' % folder.pk, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertFalse(Folder.objects.filter(pk=folder.pk).exists())
        self.assertEqual(1, len(response.redirect_chain))
        self.assertTrue(response.redirect_chain[0][0].endswith('/documents/folders'))

    def test_deleteview02(self): #a doc inside protect from deletion
        folder = Folder.objects.create(user=self.user, title='PDF',
                                       description='Contains PDF files',
                                       parent_folder=None,
                                       category=FolderCategory.objects.all()[0]
                                      )

        title = 'Boring title'
        filedata = self._build_filedata('Yes I am the content (FolderTestCase.test_deleteview02)')
        response = self.client.post('/documents/document/add', follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  'Boring description too',
                                          'filedata':     filedata.file,
                                          'folder':       folder.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        doc = self.get_object_or_fail(Document, title=title)
        self.assertEqual(folder, doc.folder)

        self.assertEqual(200, #404
                         self.client.post('/creme_core/entity/delete/%s' % folder.pk).status_code
                        )
        self.get_object_or_fail(Folder, pk=folder.pk)

        doc.filedata.delete(doc.filedata) #clean
