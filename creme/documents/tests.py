# -*- coding: utf-8 -*-

from tempfile import NamedTemporaryFile

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext

from creme_core.models import CremeEntity, RelationType, Relation, HeaderFilter
from creme_core.tests.base import CremeTestCase

from documents.models import *
from documents.constants import *


class DocumentTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'documents')

    def test_populate(self):
        self.assert_(RelationType.objects.filter(pk=REL_SUB_RELATED_2_DOC).exists())

        get_ct = ContentType.objects.get_for_model
        self.assert_(HeaderFilter.objects.filter(entity_type=get_ct(Document)).exists())

        self.assert_(Folder.objects.exists())
        self.assert_(FolderCategory.objects.exists())

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

        self.failIf(Document.objects.all())

        url = '/documents/document/add'
        self.assertEqual(200, self.client.get(url).status_code)

        title       = 'Test doc'
        description = 'Test description'
        content     = """Yes I am the content"""
        filedata    = self._build_filedata(content)
        folder      = Folder.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'filedata':     filedata.file,
                                            'folder':       folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        docs = Document.objects.all()
        self.assertEqual(1, len(docs))

        doc = docs[0]
        self.assertEqual(title,        doc.title)
        self.assertEqual(description,  doc.description)
        self.assertEqual(folder.id,    doc.folder.id)

        filedata = doc.filedata
        filedata.open()
        self.assertEqual([content], filedata.readlines())

        filedata.delete() #clean

    def test_edit_document(self):
        self.login()

        title       = 'Test doc'
        description = 'Test description'
        content     = """Yes I am the content"""
        filedata    = self._build_filedata(content)
        folder      = Folder.objects.all()[0]
        self.client.post('/documents/document/add',
                         data={
                                'user':         self.user.pk,
                                'title':        title,
                                'description':  description,
                                'filedata':     filedata.file,
                                'folder':       folder.id,
                              }
                        )

        try:
            doc = Document.objects.all()[0]
        except Exception, e:
            self.fail(str(e))

        url = '/documents/document/edit/%s' % doc.id
        self.assertEqual(200, self.client.get(url).status_code)

        title       = title.upper()
        description = description.upper()
        content     = content.upper()
        folder      = Folder.objects.create(title=u'Test folder', parent_folder=None,
                                            category=FolderCategory.objects.all()[0],
                                            user=self.user,
                                           )
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  description,
                                            'folder':       folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(1, len(response.redirect_chain))

        doc = Document.objects.get(pk=doc.id) #refresh
        self.assertEqual(title,        doc.title)
        self.assertEqual(description,  doc.description)
        self.assertEqual(folder.id,    doc.folder.id)

        doc.filedata.delete() #clean

    def test_add_related_document(self):
        self.login()

        entity = CremeEntity.objects.create(user=self.user)

        url = '/documents/document/add_related?entity_id=%s' % entity.id
        self.assertEqual(200, self.client.get(url).status_code)

        title    = 'Related doc'
        filedata = self._build_filedata("""Yes I am the content""")
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'title':        title,
                                            'description':  'Test description',
                                            'filedata':     filedata.file,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            doc = Document.objects.get(title=title)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(1, Relation.objects.filter(subject_entity=entity,
                                                    type=REL_SUB_RELATED_2_DOC,
                                                    object_entity=doc)\
                                            .count()
                        )

        doc.filedata.delete() #clean

    def test_add_folder(self):
        self.login()

        url = '/documents/folder/add'
        self.assertEqual(200, self.client.get(url).status_code)

        title = 'Test folder'

        self.failIf(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        parent      = Folder.objects.all()[0]
        category    = FolderCategory.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={
                                            'user':          self.user.pk,
                                            'title':         title,
                                            'description':   description,
                                            'parent_folder': parent.id,
                                            'category':      category.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        try:
            folder = Folder.objects.get(title=title)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(description, folder.description)
        self.assertEqual(parent.id,   folder.parent_folder.id)
        self.assertEqual(category.id, folder.category.id)

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
                                    data={
                                            'user':          self.user.pk,
                                            'title':         title,
                                            'description':   description,
                                            'parent_folder': parent.id,
                                            'category':      category.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        folder = Folder.objects.get(pk=folder.pk) #refresh
        self.assertEqual(title,       folder.title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent.id,   folder.parent_folder.id)
        self.assertEqual(category.id, folder.category.id)

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

