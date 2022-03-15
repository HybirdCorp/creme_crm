# -*- coding: utf-8 -*-

from functools import partial

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui import actions
from creme.creme_core.models import FakeOrganisation, SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents import constants
from creme.documents.actions import ExploreFolderAction
from creme.documents.bricks import ChildFoldersBrick, FolderDocsBrick
from creme.documents.models import FolderCategory

from .base import (
    Folder,
    _DocumentsTestCase,
    skipIfCustomDocument,
    skipIfCustomFolder,
)


@skipIfCustomDocument
@skipIfCustomFolder
class FolderTestCase(BrickTestCaseMixin, _DocumentsTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ADD_URL  = reverse('documents__create_folder')
        cls.LIST_URL = reverse('documents__list_folders')

    def test_createview01(self):
        "No parent folder."
        user = self.login()
        url = self.ADD_URL
        response = self.assertGET200(url)
        self.assertEqual(_('Create a folder'), response.context.get('title'))

        title = 'Test folder'
        self.assertFalse(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':        user.pk,
                'title':       title,
                'description': description,
            },
        )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertIsNone(folder.parent_folder)
        self.assertIsNone(folder.category)

    def test_createview02(self):
        "Parent folder"
        user = self.login()
        url = self.ADD_URL

        category = FolderCategory.objects.all()[0]
        parent_title = 'Test parent folder'
        self.assertFalse(Folder.objects.filter(title=parent_title).exists())

        parent = Folder.objects.create(user=user, title=parent_title, category=category)

        title = 'Test folder'
        self.assertFalse(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        other_cat = FolderCategory.objects.exclude(id=category.id)[0]
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'description':   description,
                'parent_folder': parent.id,
                'category':      other_cat.id,
            },
        )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)
        self.assertEqual(other_cat,   folder.category)

    def test_createview03(self):
        "Parent folder's' category is copied if no category"
        user = self.login()

        category = FolderCategory.objects.all()[0]
        parent_title = 'Test parent folder'
        self.assertFalse(Folder.objects.filter(title=parent_title).exists())

        parent = Folder.objects.create(user=user, title=parent_title, category=category)

        title = 'Test folder'
        response = self.client.post(
            self.ADD_URL,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'description':   'Test description',
                'parent_folder': parent.id,
            },
        )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(category, folder.category)

    def test_create_child01(self):
        user = self.login()

        create_folder = partial(Folder.objects.create, user=user, parent_folder=None)
        parent = create_folder(title='Parent folder', description='Parent description')
        unused = create_folder(title='Unused parent', description='Unused description')

        url = reverse('documents__create_folder', args=(parent.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Create a sub-folder for «{entity}»').format(entity=parent),
            context.get('title'),
        )
        self.assertEqual(Folder.save_label, context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
        self.assertNotIn('parent_folder', fields)

        title = 'Child folder'
        description = 'Child description'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'description':   description,
                'parent_folder': unused.id,  # Should not be used
            },
        )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)

    def test_create_child02(self):
        "Link credentials needed"
        user = self.login(
            is_superuser=False, allowed_apps=['documents'], creatable_models=[Folder],
        )
        sc = SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
        )

        parent = Folder.objects.create(user=user, title='Parent folder')
        url = reverse('documents__create_folder', args=(parent.id,))
        self.assertGET403(url)

        sc.value = EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK
        sc.save()
        self.assertGET200(url)

    def test_create_child03(self):
        "Creation credentials needed."
        user = self.login(
            is_superuser=False, allowed_apps=['documents'],
            # creatable_models=[Folder],
        )
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
        )

        parent = Folder.objects.create(user=user, title='Parent folder')
        self.assertGET403(reverse('documents__create_folder', args=(parent.id,)))

    def test_create_child04(self):
        "Not related to a Folder"
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='I am not a folder')
        self.assertGET404(reverse('documents__create_folder', args=(orga.id,)))

    def test_create_child_popup01(self):
        user = self.login()

        create_folder = partial(Folder.objects.create, user=user, parent_folder=None)
        parent = create_folder(title='Parent folder', description='Parent description')
        unused = create_folder(title='Unused parent', description='Unused description')

        url = reverse('documents__create_child_folder', args=(parent.id,))
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Create a sub-folder for «{entity}»').format(entity=parent),
            context.get('title'),
        )
        self.assertEqual(Folder.save_label, context.get('submit_label'))

        title = 'Child folder'
        description = 'Child description'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'description':   description,
                'parent_folder': unused.id,  # Should not be used
            },
        )
        self.assertNoFormError(response)

        folder = self.get_object_or_fail(Folder, title=title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)

    def test_create_child_popup02(self):
        "Link credentials needed"
        user = self.login(
            is_superuser=False, allowed_apps=['documents'], creatable_models=[Folder],
        )
        sc = SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
        )

        parent = Folder.objects.create(user=user, title='Parent folder')
        url = reverse('documents__create_child_folder', args=(parent.id,))
        self.assertGET403(url)

        sc.value = EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK
        sc.save()
        self.assertGET200(url)

    def test_create_child_popup03(self):
        "Creation credentials needed"
        user = self.login(
            is_superuser=False, allowed_apps=['documents'],
            # creatable_models=[Folder],
        )
        SetCredentials.objects.create(
            role=self.role,
            set_type=SetCredentials.ESET_ALL,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
        )

        parent = Folder.objects.create(user=user, title='Parent folder')
        self.assertGET403(reverse('documents__create_child_folder', args=(parent.id,)))

    def test_create_child_popup04(self):
        "Not related to a Folder"
        user = self.login()

        orga = FakeOrganisation.objects.create(user=user, name='I am not a folder')
        self.assertGET404(reverse('documents__create_child_folder', args=(orga.id,)))

    def test_editview01(self):
        user = self.login()
        title = 'Test folder'
        description = 'Test description'
        folder = Folder.objects.create(
            title=title,
            description=description,
            parent_folder=None,
            user=user,
        )

        url = folder.get_edit_absolute_url()
        self.assertGET200(url)

        title += ' edited'
        description = description.upper()
        parent = Folder.objects.all()[0]
        category = parent.category
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'description':   description,
                'parent_folder': parent.id,
                'category':      category.id,
            },
        )
        self.assertNoFormError(response)

        folder = self.refresh(folder)
        self.assertEqual(title,       folder.title)
        self.assertEqual(description, folder.description)
        self.assertEqual(parent,      folder.parent_folder)
        self.assertEqual(category,    folder.category)

    def test_editview02(self):
        "A folder cannot be its own parent."
        user = self.login()
        folder = Folder.objects.create(
            title='Test folder',
            description='Test description',
            parent_folder=None,
            user=user,
        )

        # self.assertNoFormError(self.client.post(
        #     folder.get_edit_absolute_url(),
        #     follow=True,
        #     data={
        #         'user':          user.pk,
        #         'title':         folder.title,
        #         'description':   folder.description,
        #         'parent_folder': folder.id,
        #     },
        # ))
        # self.assertIsNone(self.refresh(folder).parent_folder)
        response = self.assertPOST200(
            folder.get_edit_absolute_url(),
            follow=True,
            data={
                'user':          user.pk,
                'title':         folder.title,
                'description':   folder.description,
                'parent_folder': folder.id,
            },
        )
        self.assertFormError(
            response, 'form', 'parent_folder',
            _('«%(entity)s» violates the constraints.') % {'entity': folder},
        )

    def test_editview03(self):
        "A folder cannot be the parent of one of its parents."
        user = self.login()
        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Test folder#3', parent_folder=folder2)

        response = self.assertPOST200(
            folder1.get_edit_absolute_url(),
            follow=True,
            data={
                'user':          user.pk,
                'title':         folder1.title,
                'description':   folder1.description,
                'parent_folder': folder3.id,
            },
        )
        self.assertFormError(
            response, 'form', 'parent_folder',
            _('This folder is one of the child folders of «%(folder)s»') % {
                'folder': folder1,
            },
        )
        self.assertIsNone(self.refresh(folder1).parent_folder)

    def test_inneredit_parent01(self):
        user = self.login()
        cat1, cat2 = FolderCategory.objects.all()[:2]

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1', category=cat1)
        folder2 = create_folder(title='Test folder#2', category=cat2)

        url = self.build_inneredit_url(folder1, 'parent_folder')
        self.assertGET200(url)

        response = self.client.post(url, data={'field_value': folder2.pk})
        self.assertNoFormError(response)

        folder1 = self.refresh(folder1)
        self.assertEqual(folder2, folder1.parent_folder)
        self.assertEqual(cat1,    folder1.category)

    def test_inneredit_parent02(self):
        "The category of the parent is copied if there is none."
        user = self.login()
        cat = FolderCategory.objects.all()[0]

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', category=cat)

        response = self.client.post(
            self.build_inneredit_url(folder1, 'parent_folder'),
            data={'field_value': folder2.pk},
        )
        self.assertNoFormError(response)

        folder1 = self.refresh(folder1)
        self.assertEqual(folder2, folder1.parent_folder)
        self.assertEqual(cat,     folder1.category)

    def test_inneredit_parent03(self):
        "Loops."
        user = self.login()

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Test folder#3', parent_folder=folder2)

        url = self.build_inneredit_url(folder1, 'parent_folder')
        response1 = self.assertPOST200(url, data={'field_value': folder3.id})
        self.assertFormError(
            response1, 'form', None,
            '{} : {}'.format(
                _('Parent folder'),
                _('This folder is one of the child folders of «%(folder)s»') % {
                    'folder': folder1,
                },
            ),
        )

        # -----
        response2 = self.client.post(url, data={'field_value': folder1.pk})
        # self.assertNoFormError(response2)
        # self.assertIsNone(self.refresh(folder1).parent_folder)
        self.assertFormError(
            response2, 'form', 'field_value',
            _('«%(entity)s» violates the constraints.') % {'entity': folder1},
        )

    def test_bulkedit_parent(self):
        user = self.login()

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Test folder#3', parent_folder=folder2)
        folder4 = create_folder(title='Test folder#4')

        url = self.build_bulkupdate_url(Folder, 'parent_folder')
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'field_value': folder3.id,
                'entities':    [folder1.id, folder3.id, folder4.id],
            },
        )
        self.assertContains(
            response,
            _('This folder is one of the child folders of «%(folder)s»') % {
                'folder': folder1,
            },
        )
        self.assertContains(
            response,
            _('«%(folder)s» cannot be its own parent') % {'folder': folder3},
        )

        self.assertIsNone(self.refresh(folder1).parent_folder)
        self.assertEqual(folder2, self.refresh(folder3).parent_folder)
        self.assertEqual(folder3, self.refresh(folder4).parent_folder)

    def test_listview01(self):
        user = self.login()
        category = FolderCategory.objects.all()[0]

        create_folder = partial(
            Folder.objects.create, user=user, parent_folder=None, category=category,
        )
        folder1 = create_folder(title='PDF', description='Contains PDF files')
        folder2 = create_folder(title='SVG', description='Contains SVG files')

        response = self.assertGET200(self.LIST_URL)

        with self.assertNoException():
            context = response.context
            # folders = context['entities'].object_list
            folders = context['page_obj'].object_list
            title = context['list_title']

        self.assertIn(folder1, folders)
        self.assertIn(folder2, folders)

        self.assertEqual(
            _('List of {models}').format(models=Folder._meta.verbose_name_plural),
            title,
        )

        with self.assertRaises(KeyError):
            context['list_sub_title']  # NOQA

    def test_listview02(self):
        "With parent constraint."
        user = self.login()
        cat = FolderCategory.objects.all()[0]

        create_folder = partial(Folder.objects.create, user=user, category=cat)
        grand_parent = create_folder(title='Docs', description='Contains docs')
        parent = create_folder(
            title='Vectors', description='Contains Vector docs', parent_folder=grand_parent,
        )
        folder1 = create_folder(
            title='PDF', description='Contains PDF files', parent_folder=parent,
        )
        folder2 = create_folder(
            title='SVG', description='Contains SVG files', parent_folder=parent,
        )

        parent2 = create_folder(title='Raster', description='Contains Raster gfx')
        folder3 = create_folder(
            title='BMP', description='Contains BMP files', parent_folder=parent2,
        )

        response = self.assertGET200(self.LIST_URL, data={'parent_id': parent.id})

        with self.assertNoException():
            context = response.context
            folders = context['page_obj'].object_list
            title = context['list_title']
            sub_title = context['sub_title']

        self.assertIn(folder1, folders)
        self.assertIn(folder2, folders)
        self.assertNotIn(grand_parent, folders)
        self.assertNotIn(parent,  folders)
        self.assertNotIn(folder3, folders)
        self.assertNotIn(parent2, folders)

        self.assertEqual(_('List of sub-folders for «{parent}»').format(parent=parent), title)
        self.assertEqual(f'{grand_parent.title} > {parent.title}', sub_title)

        # ------
        response = self.assertGET200(self.LIST_URL, data={'parent_id': 'invalid'})

        with self.assertNoException():
            folders = response.context['page_obj'].object_list

        self.assertNotIn(folder1,   folders)
        self.assertIn(grand_parent, folders)

    def test_listview_actions(self):
        user = self.login()
        folder = Folder.objects.create(user=user, title='My folder')

        explore_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=folder)
            if isinstance(action, ExploreFolderAction)
        ]
        self.assertEqual(1, len(explore_actions))

        explore_action = explore_actions[0]
        self.assertEqual('redirect', explore_action.type)
        self.assertEqual(
            '{}?parent_id={}'.format(folder.get_lv_absolute_url(), folder.id),
            explore_action.url
        )
        self.assertTrue(explore_action.is_enabled)
        self.assertTrue(explore_action.is_visible)
        self.assertEqual(
            _('List sub-folders of «{}»').format(folder), explore_action.help_text
        )

    def test_folder_clone01(self):
        user = self.login()
        title = 'folder'
        folder = Folder.objects.create(user=user, title=title, description='d')

        stack = [folder]
        stack_append = stack.append

        for i in range(100):
            clone = folder.clone()
            self.assertNotEqual(stack[-1].title, clone.title)
            stack_append(clone)

    def test_deleteview01(self):
        "No doc inside."
        user = self.login()

        folder = Folder.objects.create(user=user, title='ToBeDel', description='remove me')
        folder.trash()

        response = self.assertPOST200(folder.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(folder)
        self.assertRedirects(response, self.LIST_URL)

    def test_deleteview02(self):
        "A doc inside protect from deletion."
        user = self.login()

        folder = Folder.objects.create(user=user, title='ToBeDel', description='remove me')

        title = 'Boring title'
        doc = self._create_doc(title, folder=folder)
        self.assertEqual(folder, doc.linked_folder)

        folder.trash()

        self.assertPOST409(folder.get_delete_absolute_url())
        self.assertStillExists(folder)

    def test_deleteview03(self):
        "Un deletable folder: 'Creme'."
        self.login()
        folder = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_RELATED2ENTITIES)

        self.assertPOST409(folder.get_delete_absolute_url())

    def test_deleteview04(self):
        "Un deletable folder: 'Images'."
        self.login()
        folder = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_IMAGES)

        self.assertPOST409(folder.get_delete_absolute_url())

    def test_bricks(self):
        user = self.login()

        FolderDocsBrick.page_size = max(4, settings.BLOCK_SIZE)
        ChildFoldersBrick.page_size = max(4, settings.BLOCK_SIZE)

        create_folder = partial(
            Folder.objects.create,
            user=user, category=FolderCategory.objects.all()[0],
            description='Contains PDF files',
        )
        folder = create_folder(title='PDF', description='Contains PDF files')

        child1 = create_folder(title='PDF (tutorial)', parent_folder=folder)
        child2 = create_folder(title='PDF (specifications)', parent_folder=folder)

        child3 = create_folder(title='PDF (creme)', parent_folder=child1)

        create_doc = self._create_doc
        doc1 = create_doc('Test doc #1', folder=folder)
        doc2 = create_doc('Test doc #2', folder=folder)
        doc3 = create_doc('Test doc #3')
        doc4 = create_doc('Test doc #4', folder=folder)

        doc4.trash()

        response = self.assertGET200(folder.get_absolute_url())
        tree = self.get_html_tree(response.content)

        brick_node1 = self.get_brick_node(tree, FolderDocsBrick.id_)
        self.assertInstanceLink(brick_node1, doc1)
        self.assertInstanceLink(brick_node1, doc2)
        self.assertInstanceLink(brick_node1, doc4)  # TODO: see bricks.py
        self.assertNoInstanceLink(brick_node1, doc3)

        brick_node2 = self.get_brick_node(tree, ChildFoldersBrick.id_)
        self.assertInstanceLink(brick_node2, child1)
        self.assertInstanceLink(brick_node2, child2)
        self.assertNoInstanceLink(brick_node2, child3)

    def test_merge01(self):
        user = self.login()

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
            form = response.context['form']
            fields = form.fields

        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder2, getattr(form, 'entity2', None))

        self.assertIn('title', fields)
        self.assertNotIn('parent_folder', fields)

        response = self.client.post(
            url,
            follow=True,
            data={
                'user_1':      user.id,
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
            },
        )
        self.assertNoFormError(response)

        self.assertDoesNotExist(folder2)

        with self.assertNoException():
            merged_folder = self.refresh(folder1)

        self.assertEqual(folder1.title,       merged_folder.title)
        self.assertEqual(folder2.description, merged_folder.description)
        self.assertIsNone(merged_folder.parent_folder)

        self.assertSetEqual({doc1, doc2}, {*merged_folder.document_set.all()})

    def test_merge02(self):
        "One folder is the parent of the other one"
        user = self.login()

        create_folder = partial(Folder.objects.create, user=user)
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
