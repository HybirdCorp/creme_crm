 # -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.test.utils import override_settings
    from django.utils.encoding import smart_str, smart_unicode

    from .base import _DocumentsTestCase
    from creme.documents.models import Folder, FolderCategory, Document
    from creme.documents.blocks import folder_docs_block
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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

        create_folder = partial(Folder.objects.create, user=user, 
                                parent_folder=None, category=category
                               )
        folder1 = create_folder(title='PDF', description='Contains PDF files')
        folder2 = create_folder(title='SVG', description='Contains SVG files')

        response = self.assertGET200('/documents/folders')

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

    def _create_folder_2_delete(self):
        return Folder.objects.create(user=self.user, title='PDF',
                                     description='Contains PDF files',
                                     parent_folder=None,
                                     category=FolderCategory.objects.all()[0],
                                     is_deleted=True,
                                    )

    def test_deleteview01(self):
        "No doc inside"
        folder = self._create_folder_2_delete()
        response = self.assertPOST200('/creme_core/entity/delete/%s' % folder.pk, follow=True)
        self.assertFalse(Folder.objects.filter(pk=folder.pk).exists())
        self.assertRedirects(response, '/documents/folders')

    def test_deleteview02(self):
        "A doc inside protect from deletion"
        folder = self._create_folder_2_delete()

        title = 'Boring title'
        self._create_doc(title, folder=folder, description='Boring description too',
                         file_obj=self._build_filedata('Content (FolderTestCase.test_deleteview02)')[0],
                        )

        doc = self.get_object_or_fail(Document, title=title)
        self.assertEqual(folder, doc.folder)

        self.assertPOST403('/creme_core/entity/delete/%s' % folder.pk)
        self.get_object_or_fail(Folder, pk=folder.pk)

    @override_settings(BLOCK_SIZE=max(4, settings.BLOCK_SIZE))
    def test_block(self):
        "Block which display contained docs"
        folder = Folder.objects.create(user=self.user, title='PDF',
                                       description='Contains PDF files',
                                       parent_folder=None,
                                       category=FolderCategory.objects.all()[0]
                                      )

        #TODO: factorise (see documents.test_listview too) ?
        def create_doc(title, folder=None):
            self._create_doc(title, folder=folder, description='Test description',
                             file_obj=self._build_filedata('%s : Content' % title)[0],
                            )

            return self.get_object_or_fail(Document, title=title)

        doc1 = create_doc('Test doc #1', folder)
        doc2 = create_doc('Test doc #2', folder)
        doc3 = create_doc('Test doc #3')
        doc4 = create_doc('Test doc #4', folder)

        doc4.trash()

        #if settings.BLOCK_SIZE < 4:
            #settings.BLOCK_SIZE = 4

        content = self.assertGET200(folder.get_absolute_url()).content
        block_start_index = content.find(smart_str('id="%s"' % folder_docs_block.id_))
        self.assertNotEqual(-1, block_start_index)

        body_start_index = content.find('<tbody class="collapsable">', block_start_index)
        self.assertNotEqual(-1, body_start_index)

        end_index = content.find('</tbody>', body_start_index)
        self.assertNotEqual(-1, end_index)

        block_str = smart_unicode(content[body_start_index:end_index])
        self.assertIn(doc1.title, block_str)
        self.assertIn(doc2.title, block_str)
        self.assertNotIn(doc3.title, block_str)
        #self.assertNotIn(doc4.title, block_str) TODO (see blocks.py)
