# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.core.urlresolvers import reverse
    from django.utils.encoding import smart_str, smart_unicode
    from django.utils.translation import ugettext as _

    from .base import _DocumentsTestCase, skipIfCustomDocument, skipIfCustomFolder, Folder
    from creme.documents.models import FolderCategory
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomDocument
@skipIfCustomFolder
class FolderTestCase(_DocumentsTestCase):
    @classmethod
    def setUpClass(cls):
        # _DocumentsTestCase.setUpClass()
        super(FolderTestCase, cls).setUpClass()

        cls.ADD_URL  = reverse('documents__create_folder')
        cls.LIST_URL = reverse('documents__list_folders')

    def setUp(self):
        super(FolderTestCase, self).setUp()
        self.login()

    def test_createview01(self):
        "No parent folder"
        url = self.ADD_URL
        self.assertGET200(url)

        title = 'Test folder'
        self.assertFalse(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        response = self.client.post(url, follow=True,
                                    data={'user':        self.user.pk,
                                          'title':       title,
                                          'description': description,
                                         }
                                   )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertIsNone(folder.parent_folder)
        self.assertIsNone(folder.category)

    def test_createview02(self):
        "Parent folder"
        user = self.user
        url = self.ADD_URL

        category = FolderCategory.objects.all()[0]
        parent_title = 'Test parent folder'
        self.assertFalse(Folder.objects.filter(title=parent_title).exists())

        parent = Folder.objects.create(user=user, title=parent_title, category=category)

        title = 'Test folder'
        self.assertFalse(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        other_cat = FolderCategory.objects.exclude(id=category.id)[0]
        response = self.client.post(url, follow=True,
                                    data={'user':          user.pk,
                                          'title':         title,
                                          'description':   description,
                                          'parent_folder': parent.id,
                                          'category':      other_cat.id
                                         }
                                   )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)
        self.assertEqual(other_cat,   folder.category)

    def test_createview03(self):
        "Parent folder's' category is copied if no category"
        user = self.user

        category = FolderCategory.objects.all()[0]
        parent_title = 'Test parent folder'
        self.assertFalse(Folder.objects.filter(title=parent_title).exists())

        parent = Folder.objects.create(user=user, title=parent_title, category=category)

        title = 'Test folder'
        response = self.client.post(self.ADD_URL, follow=True,
                                    data={'user':          user.pk,
                                          'title':         title,
                                          'description':   'Test description',
                                          'parent_folder': parent.id,
                                         }
                                   )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(category, folder.category)

    def test_create_child(self):
        user = self.user

        create_folder = partial(Folder.objects.create, user=user, parent_folder=None)
        parent = create_folder(title=u'Parent folder', description='Parent description')
        unused = create_folder(title=u'Unused parent', description='Unused description')

        url = reverse('documents__create_child_folder', args=(parent.id,))
        self.assertGET200(url)

        title = 'Child folder'
        description = 'Child description'
        response = self.client.post(url, follow=True,
                                    data={'user':          user.pk,
                                          'title':         title,
                                          'description':   description,
                                          'parent_folder': unused.id,  # Should not be used
                                         }
                                   )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)

    def test_editview01(self):
        title = u'Test folder'
        description = 'Test description'
        folder = Folder.objects.create(title=title,
                                       description=description,
                                       parent_folder=None,
                                       user=self.user,
                                      )

        url = folder.get_edit_absolute_url()
        self.assertGET200(url)

        title       += u' edited'
        description = description.upper()
        parent      = Folder.objects.all()[0]
        category = parent.category
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

    def test_editview02(self):
        "A folder cannot be its own parent"
        user = self.user
        folder = Folder.objects.create(title=u'Test folder',
                                       description=u'Test description',
                                       parent_folder=None,
                                       user=user,
                                      )

        response = self.client.post(folder.get_edit_absolute_url(), follow=True,
                                    data={'user':          user.pk,
                                          'title':         folder.title,
                                          'description':   folder.description,
                                          'parent_folder': folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(folder).parent_folder)

    def test_editview03(self):
        "A folder cannot be the parent of one of its parents"
        user = self.user
        create_folder = partial(Folder.objects.create, user=user,
                                description=u'Test description',
                               )
        folder1 = create_folder(title=u'Test folder#1')
        folder2 = create_folder(title=u'Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title=u'Test folder#3', parent_folder=folder2)

        response = self.assertPOST200(folder1.get_edit_absolute_url(), follow=True,
                                      data={'user':          user.pk,
                                            'title':         folder1.title,
                                            'description':   folder1.description,
                                            'parent_folder': folder3.id,
                                            }
                                    )
        self.assertFormError(response, 'form', 'parent_folder',
                             _(u'This folder is one of the child folders of «%(folder)s»') % {
                                    'folder': folder1,
                                  }
                            )
        self.assertIsNone(self.refresh(folder1).parent_folder)

    def test_inneredit_parent01(self):
        cat1, cat2 = FolderCategory.objects.all()[:2]

        create_folder = partial(Folder.objects.create, user=self.user,
                                description=u'Test description',
                               )
        folder1 = create_folder(title=u'Test folder#1', category=cat1)
        folder2 = create_folder(title=u'Test folder#2', category=cat2)

        url = self.build_inneredit_url(folder1, 'parent_folder')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': folder2.pk})
        self.assertNoFormError(response)

        folder1 = self.refresh(folder1)
        self.assertEqual(folder2, folder1.parent_folder)
        self.assertEqual(cat1,    folder1.category)

    def test_inneredit_parent02(self):
        "The category of the parent is copied if there is none"
        cat = FolderCategory.objects.all()[0]

        create_folder = partial(Folder.objects.create, user=self.user,
                                description=u'Test description',
                               )
        folder1 = create_folder(title=u'Test folder#1')
        folder2 = create_folder(title=u'Test folder#2', category=cat)

        response = self.client.post(self.build_inneredit_url(folder1, 'parent_folder'),
                                    data={'field_value': folder2.pk}
                                   )
        self.assertNoFormError(response)

        folder1 = self.refresh(folder1)
        self.assertEqual(folder2, folder1.parent_folder)
        self.assertEqual(cat,     folder1.category)

    def test_inneredit_parent03(self):
        "Loops"
        create_folder = partial(Folder.objects.create, user=self.user,
                                description=u'Test description',
                               )
        folder1 = create_folder(title=u'Test folder#1')
        folder2 = create_folder(title=u'Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title=u'Test folder#3', parent_folder=folder2)

        url = self.build_inneredit_url(folder1, 'parent_folder')
        response = self.assertPOST200(url, data={'field_value': folder3.id})
        self.assertFormError(response, 'form', None,
                             _(u'This folder is one of the child folders of «%(folder)s»') % {
                                    'folder': folder1,
                                  }
                            )

        # -----
        response = self.client.post(url, data={'field_value': folder1.pk})
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(folder1).parent_folder)

    def test_bulkedit_parent(self):
        create_folder = partial(Folder.objects.create, user=self.user,
                                description=u'Test description',
                               )
        folder1 = create_folder(title=u'Test folder#1')
        folder2 = create_folder(title=u'Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title=u'Test folder#3', parent_folder=folder2)
        folder4 = create_folder(title=u'Test folder#4')

        # url = self.build_bulkedit_url([folder1, folder3, folder4], 'parent_folder')
        url = self.build_bulkupdate_url(Folder, 'parent_folder')
        self.assertGET200(url)

        # response = self.client.post(url, data={'field_value': folder3.pk})
        response = self.client.post(url,
                                    data={'field_value': folder3.id,
                                          'entities':    [folder1.id, folder3.id, folder4.id],
                                         }
                                   )
        self.assertContains(response,
                            _(u'This folder is one of the child folders of «%(folder)s»') % {
                                    'folder': folder1,
                                  },
                            1
                           )
        self.assertContains(response,
                            _(u'«%(folder)s» cannot be its own parent') % {
                                    'folder': folder3,
                                  },
                            1
                           )

        self.assertIsNone(self.refresh(folder1).parent_folder)
        self.assertEqual(folder2, self.refresh(folder3).parent_folder)
        self.assertEqual(folder3, self.refresh(folder4).parent_folder)

    def test_listview01(self):
        user = self.user
        category = FolderCategory.objects.all()[0]

        create_folder = partial(Folder.objects.create, user=user,
                                parent_folder=None, category=category,
                               )
        folder1 = create_folder(title='PDF', description='Contains PDF files')
        folder2 = create_folder(title='SVG', description='Contains SVG files')

        response = self.assertGET200(self.LIST_URL)

        with self.assertNoException():
            context = response.context
            folders = context['entities'].object_list
            title   = context['list_title']

        self.assertIn(folder1, folders)
        self.assertIn(folder2, folders)

        self.assertEqual(_(u"List of %s") % Folder._meta.verbose_name_plural, title)

        with self.assertRaises(KeyError):
            context['list_sub_title']

    def test_listview02(self):
        "With parent constraint"
        cat = FolderCategory.objects.all()[0]

        create_folder = partial(Folder.objects.create, user=self.user, category=cat)
        grand_parent = create_folder(title='Docs', description='Contains docs')
        parent  = create_folder(title='Vectors', description='Contains Vector docs',
                                parent_folder=grand_parent,
                               )
        folder1 = create_folder(title='PDF', description='Contains PDF files',
                                parent_folder=parent,
                               )
        folder2 = create_folder(title='SVG', description='Contains SVG files',
                                parent_folder=parent,
                               )

        parent2 = create_folder(title='Raster', description='Contains Raster gfx')
        folder3 = create_folder(title='BMP', description='Contains BMP files',
                                parent_folder=parent2,
                               )

        response = self.assertGET200(self.LIST_URL, data={'parent_id': parent.id})

        with self.assertNoException():
            context = response.context
            folders   = context['entities'].object_list
            title     = context['list_title']
            sub_title = context['list_sub_title']

        self.assertIn(folder1, folders)
        self.assertIn(folder2, folders)
        self.assertNotIn(grand_parent, folders)
        self.assertNotIn(parent,  folders)
        self.assertNotIn(folder3, folders)
        self.assertNotIn(parent2, folders)

        self.assertEqual(_(u"List sub-folders of %s") % parent, title)
        self.assertEqual('%s > %s' % (grand_parent.title, parent.title),
                         sub_title
                        )

        # ------
        response = self.assertGET200(self.LIST_URL, data={'parent_id': 'invalid'})

        with self.assertNoException():
            folders = response.context['entities'].object_list

        self.assertNotIn(folder1,   folders)
        self.assertIn(grand_parent, folders)

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
        folder = Folder.objects.create(user=self.user, title='ToBeDel', description="remove me")
        folder.trash()

        response = self.assertPOST200('/creme_core/entity/delete/%s' % folder.pk, follow=True)
        self.assertDoesNotExist(folder)
        self.assertRedirects(response, self.LIST_URL)

    def test_deleteview02(self):
        "A doc inside protect from deletion"
        folder = Folder.objects.create(user=self.user, title='ToBeDel', description="remove me")

        title = 'Boring title'
        doc = self._create_doc(title, folder=folder)
        self.assertEqual(folder, doc.folder)

        folder.trash()

        self.assertPOST403('/creme_core/entity/delete/%s' % folder.pk)
        self.assertStillExists(folder)

    def test_block(self):
        "Block which display contained docs"
        from creme.documents.blocks import folder_docs_block

        folder_docs_block.page_size = max(4, settings.BLOCK_SIZE)

        folder = Folder.objects.create(user=self.user, title='PDF',
                                       description='Contains PDF files',
                                       parent_folder=None,
                                       category=FolderCategory.objects.all()[0]
                                      )

        create_doc = self._create_doc
        doc1 = create_doc('Test doc #1', folder=folder)
        doc2 = create_doc('Test doc #2', folder=folder)
        doc3 = create_doc('Test doc #3')
        doc4 = create_doc('Test doc #4', folder=folder)

        doc4.trash()

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
        # self.assertNotIn(doc4.title, block_str) TODO (see blocks.py)

    def test_merge01(self):
        user = self.user

        create_folder = partial(Folder.objects.create, user=user)
        folder1 = create_folder(title='Folder#1', description='Folder#1')
        folder2 = create_folder(title='Folder#2', description='Folder#2')
        folder3 = create_folder(title='Folder#3', description='Folder#3')

        create_doc = self._create_doc
        doc1 = create_doc('Test doc #1', folder=folder1)
        doc2 = create_doc('Test doc #2', folder=folder2)

        url = self.build_merge_url(folder1, folder2)
        response = self.assertGET200(url)

        with self.assertNoException():
            form   = response.context['form']
            fields = form.fields

        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder2, getattr(form, 'entity2', None))

        self.assertIn('title', fields)
        self.assertNotIn('parent_folder', fields)

        response = self.client.post(url, follow=True,
                                    data={'user_1':      user.id,
                                          'user_2':      user.id,
                                          'user_merged': user.id,

                                          'title_1':      folder1.title,
                                          'title_2':      folder2.title,
                                          'title_merged': folder1.title,

                                          'description_1':      folder1.description,
                                          'description_2':      folder2.description,
                                          'description_merged': folder2.description,

                                          # Should be ignored
                                          'parent_folder_1':      '',
                                          'parent_folder_2':      '',
                                          'parent_folder_merged': folder3.id,
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertDoesNotExist(folder2)

        with self.assertNoException():
            merged_folder = self.refresh(folder1)

        self.assertEqual(folder1.title,       merged_folder.title)
        self.assertEqual(folder2.description, merged_folder.description)
        self.assertIsNone(merged_folder.parent_folder)

        self.assertEqual({doc1, doc2}, set(merged_folder.document_set.all()))

    def test_merge02(self):
        "One folder is the parent of the other one"
        create_folder = partial(Folder.objects.create, user=self.user)
        folder1 = create_folder(title='Folder#1', description='Folder#1')
        folder2 = create_folder(title='Folder#2', description='Folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Folder#3', description='Folder#3', parent_folder=folder2)

        build_url = self.build_merge_url
        response = self.assertGET200(build_url(folder1, folder3))

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder3, getattr(form, 'entity2', None))

        # -------------
        form = self.assertGET200(build_url(folder3, folder1)).context['form']

        # Swapped
        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder3, getattr(form, 'entity2', None))
