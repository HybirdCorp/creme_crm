# -*- coding: utf-8 -*-

try:
    from tempfile import NamedTemporaryFile
    from django.contrib.auth.models import User

    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext

    from creme_core.models import CremeEntity, RelationType, Relation, HeaderFilter, HistoryLine
    from creme_core.tests.base import CremeTestCase

    from documents.models import *
    from documents.constants import *
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class DocumentTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'documents')

    def test_populate(self):
        self.assertTrue(RelationType.objects.filter(pk=REL_SUB_RELATED_2_DOC).exists())

        get_ct = ContentType.objects.get_for_model
        self.assert_(HeaderFilter.objects.filter(entity_type=get_ct(Document)).exists())

        self.assertTrue(Folder.objects.exists())
        self.assertTrue(FolderCategory.objects.exists())

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/documents/').status_code)

    def _build_filedata(self, content_str):
        tmpfile = NamedTemporaryFile()
        tmpfile.write(content_str)
        tmpfile.flush()

        filedata = tmpfile.file
        filedata.seek(0)

        return tmpfile

    def test_add_document(self):
        self.login()

        self.assertFalse(Document.objects.exists())

        url = '/documents/document/add'
        self.assertEqual(200, self.client.get(url).status_code)

        title       = 'Test doc'
        description = 'Test description'
        content     = """Yes I am the content"""
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

    def test_edit_document(self):
        self.login()

        title       = 'Test doc'
        description = 'Test description'
        content     = """Yes I am the content"""
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

    def test_add_related_document(self):
        self.login()

        entity = CremeEntity.objects.create(user=self.user)

        url = '/documents/document/add_related/%s' % entity.id
        self.assertEqual(200, self.client.get(url).status_code)

        title    = 'Related doc'
        filedata = self._build_filedata("Yes I am the content")
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'title':        title,
                                          'description':  'Test description',
                                          'filedata':     filedata.file,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            doc = Document.objects.get(title=title)

        self.assertRelationCount(1, entity, REL_SUB_RELATED_2_DOC, doc)

        doc.filedata.delete(doc.filedata) #clean

    def test_add_folder(self):
        self.login()

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

    def test_edit_folder(self):
        self.login()

        title = u'Test folder'
        description='Test description'
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

class FolderTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'documents')

    def test_folder_clone01(self):
        self.login()
        title = 'folder'
        folder = Folder.objects.create(user=self.user, title=title, description="d")

        stack = [folder]
        stack_append = stack.append

        for i in xrange(100):
            clone = folder.clone()
            self.assertNotEqual(stack[-1].title, clone.title)
            stack_append(clone)

