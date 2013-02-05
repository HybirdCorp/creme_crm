 # -*- coding: utf-8 -*-

try:
    from documents.tests.base import _DocumentsTestCase
    from documents.models import Folder, FolderCategory, Document
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all_ = ('FolderTestCase',)


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
