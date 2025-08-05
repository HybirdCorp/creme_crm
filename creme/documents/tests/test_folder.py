from functools import partial

from django.conf import settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms import CreatorEntityField
from creme.creme_core.gui import actions
from creme.creme_core.models import (
    FakeOrganisation,
    FieldsConfig,
    SetCredentials,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents import constants
from creme.documents.actions import ExploreFolderAction
from creme.documents.bricks import ChildFoldersBrick, FolderDocsBrick
from creme.documents.deletors import FolderDeletor
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

    def test_save(self):
        user = self.get_root_user()
        title = 'Test folder'
        create_folder = partial(Folder.objects.create, user=user)
        folder = create_folder(title=title)
        self.assertEqual(user,  folder.user)
        self.assertEqual(title, folder.title)
        self.assertFalse(folder.description)
        self.assertIsNone(folder.parent_folder)
        self.assertIsNone(folder.category)

        category = FolderCategory.objects.first()
        self.assertIsNotNone(category)

        parent_folder = create_folder(title='Parent', category=category)
        self.assertEqual(category, parent_folder.category)

        folder.parent_folder = parent_folder
        folder.save(update_fields=['parent_folder'])
        folder.refresh_from_db()
        self.assertEqual(parent_folder, folder.parent_folder)
        self.assertEqual(category,      folder.category)

    def test_createview01(self):
        "No parent folder."
        user = self.login_as_root_and_get()
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
        "Parent folder."
        user = self.login_as_root_and_get()
        url = self.ADD_URL

        category = FolderCategory.objects.all()[0]
        parent_title = 'Test parent folder'
        self.assertFalse(Folder.objects.filter(title=parent_title).exists())

        parent = Folder.objects.create(user=user, title=parent_title, category=category)

        title = 'Test folder'
        self.assertFalse(Folder.objects.filter(title=title).exists())

        description = 'Test description'
        other_cat = FolderCategory.objects.create(name='Other')
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
        user = self.login_as_root_and_get()

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
        user = self.login_as_root_and_get()

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
        user = self.login_as_standard(
            allowed_apps=['documents'], creatable_models=[Folder],
        )
        sc = SetCredentials.objects.create(
            role=user.role,
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
        user = self.login_as_standard(allowed_apps=['documents'])
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        parent = Folder.objects.create(user=user, title='Parent folder')
        self.assertGET403(reverse('documents__create_folder', args=(parent.id,)))

    def test_create_child04(self):
        "Not related to a Folder."
        user = self.login_as_root_and_get()

        orga = FakeOrganisation.objects.create(user=user, name='I am not a folder')
        self.assertGET404(reverse('documents__create_folder', args=(orga.id,)))

    def test_create_child_popup01(self):
        user = self.login_as_root_and_get()

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
        user = self.login_as_standard(
            allowed_apps=['documents'], creatable_models=[Folder],
        )
        sc = SetCredentials.objects.create(
            role=user.role,
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
        "Creation credentials needed."
        user = self.login_as_standard(allowed_apps=['documents'])
        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'LINK'])

        parent = Folder.objects.create(user=user, title='Parent folder')
        self.assertGET403(reverse('documents__create_child_folder', args=(parent.id,)))

    def test_create_child_popup04(self):
        "Not related to a Folder"
        user = self.login_as_root_and_get()

        orga = FakeOrganisation.objects.create(user=user, name='I am not a folder')
        self.assertGET404(reverse('documents__create_child_folder', args=(orga.id,)))

    def test_editview01(self):
        user = self.login_as_root_and_get()
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
        user = self.login_as_root_and_get()
        folder = Folder.objects.create(
            title='Test folder',
            description='Test description',
            parent_folder=None,
            user=user,
        )

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
            self.get_form_or_fail(response),
            field='parent_folder',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': folder},
        )

    def test_editview03(self):
        "A folder cannot be the parent of one of its parents."
        user = self.login_as_root_and_get()
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
            self.get_form_or_fail(response),
            field='parent_folder',
            errors=_('This folder is one of the child folders of «%(folder)s»') % {
                'folder': folder1,
            },
        )
        self.assertIsNone(self.refresh(folder1).parent_folder)

    def test_inneredit_parent01(self):
        user = self.login_as_root_and_get()

        FieldsConfig.objects.create(
            content_type=Folder,
            descriptions=[('description', {FieldsConfig.REQUIRED: True})],
        )  # Should not be used

        cat1 = FolderCategory.objects.all()[0]
        cat2 = FolderCategory.objects.create(name='Other')

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1', category=cat1)
        folder2 = create_folder(title='Test folder#2', category=cat2)

        field_name = 'parent_folder'
        uri = self.build_inneredit_uri(folder1, field_name)
        response1 = self.assertGET200(uri)
        formfield_name = f'override-{field_name}'

        with self.assertNoException():
            parent_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(parent_f, CreatorEntityField)
        self.assertIsNone(parent_f.initial)
        self.assertFalse(parent_f.required)

        # ----
        response2 = self.client.post(uri, data={formfield_name: folder2.pk})
        self.assertNoFormError(response2)

        folder1 = self.refresh(folder1)
        self.assertEqual(folder2, folder1.parent_folder)
        self.assertEqual(cat1,    folder1.category)

    def test_inneredit_parent02(self):
        "The category of the parent is copied if there is none."
        user = self.login_as_root_and_get()
        cat = FolderCategory.objects.all()[0]

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', category=cat)

        field_name = 'parent_folder'
        response = self.client.post(
            self.build_inneredit_uri(folder1, field_name),
            data={f'override-{field_name}': folder2.pk},
        )
        self.assertNoFormError(response)

        folder1 = self.refresh(folder1)
        self.assertEqual(folder2, folder1.parent_folder)
        self.assertEqual(cat,     folder1.category)

    def test_inneredit_parent03(self):
        "Loops."
        user = self.login_as_root_and_get()

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Test folder#3', parent_folder=folder2)

        field_name = 'parent_folder'
        uri = self.build_inneredit_uri(folder1, field_name)
        formfield_name = f'override-{field_name}'
        response1 = self.assertPOST200(uri, data={formfield_name: folder3.id})
        self.assertFormError(
            response1.context['form'],
            field=None,
            errors=_(
                'This folder is one of the child folders of «%(folder)s»'
            ) % {'folder': folder1},
        )

        # -----
        response2 = self.client.post(uri, data={formfield_name: folder1.pk})
        self.assertFormError(
            response2.context['form'],
            field=formfield_name,
            errors=_('«%(entity)s» violates the constraints.') % {'entity': folder1},
        )

    def test_inneredit_parent04(self):
        "Initial not None."
        user = self.login_as_root_and_get()

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', parent_folder=folder1)

        field_name = 'parent_folder'
        response = self.assertGET200(self.build_inneredit_uri(folder2, field_name))

        with self.assertNoException():
            parent_f = response.context['form'].fields[f'override-{field_name}']

        self.assertEqual(folder1.id, parent_f.initial)

    def test_inneredit_parent05(self):
        "Configured as required."
        user = self.login_as_root_and_get()

        field_name = 'parent_folder'
        FieldsConfig.objects.create(
            content_type=Folder,
            descriptions=[(field_name, {FieldsConfig.REQUIRED: True})],
        )

        cat = FolderCategory.objects.first()
        folder = Folder.objects.create(user=user, title='Test folder#1', category=cat)

        response = self.assertGET200(self.build_inneredit_uri(folder, field_name))

        with self.assertNoException():
            parent_f = response.context['form'].fields[f'override-{field_name}']

        self.assertTrue(parent_f.required)

    def test_bulkedit_parent(self):
        user = self.login_as_root_and_get()

        create_folder = partial(
            Folder.objects.create, user=user, description='Test description',
        )
        folder1 = create_folder(title='Test folder#1')
        folder2 = create_folder(title='Test folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Test folder#3', parent_folder=folder2)
        folder4 = create_folder(title='Test folder#0')  # First by title

        folders = [folder1, folder3, folder4]
        field_name = 'parent_folder'
        url = self.build_bulkupdate_uri(model=Folder, field=field_name)
        self.assertGET200(url)

        # ---
        formfield_name = f'override-{field_name}'
        response2 = self.client.post(
            url,
            data={
                'entities': [folder.id for folder in folders],
                formfield_name: folder3.id,
            },
        )
        self.assertNoFormError(response2)
        self.assertContains(
            response2,
            _('This folder is one of the child folders of «%(folder)s»') % {
                'folder': folder1,
            },
        )
        self.assertContains(
            response2,
            _('«%(folder)s» cannot be its own parent') % {'folder': folder3},
        )

        self.assertIsNone(self.refresh(folder1).parent_folder)
        self.assertEqual(folder2, self.refresh(folder3).parent_folder)
        self.assertEqual(folder3, self.refresh(folder4).parent_folder)

    def test_listview01(self):
        user = self.login_as_root_and_get()
        category = FolderCategory.objects.all()[0]

        create_folder = partial(
            Folder.objects.create, user=user, parent_folder=None, category=category,
        )
        folder1 = create_folder(title='PDF', description='Contains PDF files')
        folder2 = create_folder(title='SVG', description='Contains SVG files')

        response = self.assertGET200(self.LIST_URL)

        with self.assertNoException():
            context = response.context
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
        user = self.login_as_root_and_get()
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
        user = self.login_as_root_and_get()
        folder = Folder.objects.create(user=user, title='My folder')

        explore_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=folder)
            if isinstance(action, ExploreFolderAction)
        )
        self.assertEqual('redirect', explore_action.type)
        self.assertEqual(
            f'{folder.get_lv_absolute_url()}?parent_id={folder.id}',
            explore_action.url
        )
        self.assertTrue(explore_action.is_enabled)
        self.assertTrue(explore_action.is_visible)
        self.assertEqual(
            _('List sub-folders of «{}»').format(folder),
            explore_action.help_text,
        )

    def test_clone(self):
        user = self.login_as_root_and_get()
        title = 'folder'
        folder = Folder.objects.create(user=user, title=title, description='d')

        stack = [folder]
        stack_append = stack.append

        for i in range(10):
            cloned_folder = self.clone(folder)

            self.assertNotEqual(stack[-1].title, cloned_folder.title)
            stack_append(cloned_folder)

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #     title = 'folder'
    #     folder = Folder.objects.create(user=user, title=title, description='d')
    #
    #     stack = [folder]
    #     stack_append = stack.append
    #
    #     for i in range(100):
    #         clone = folder.clone()
    #         self.assertNotEqual(stack[-1].title, clone.title)
    #         stack_append(clone)
    #
    #     self.assertTrue(getattr(folder.clone, 'alters_data', False))

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview__empty(self):
        "No doc inside."
        user = self.login_as_root_and_get()

        folder = Folder.objects.create(user=user, title='ToBeDel', description='remove me')
        folder.trash()

        response = self.assertPOST200(folder.get_delete_absolute_url(), follow=True)
        self.assertDoesNotExist(folder)
        self.assertRedirects(response, self.LIST_URL)

        self.assertTrue(getattr(folder.trash, 'alters_data', False))

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview__one_doc(self):
        "A doc inside protect from deletion."
        user = self.login_as_root_and_get()

        folder = Folder.objects.create(user=user, title='ToBeDel', description='remove me')

        title = 'Boring title'
        doc = self._create_doc(user=user, title=title, folder=folder)
        self.assertEqual(folder, doc.linked_folder)

        folder.trash()

        self.assertPOST409(folder.get_delete_absolute_url())
        self.assertStillExists(folder)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview__one_child_folder(self):
        "Folder contains a folder."
        user = self.login_as_root_and_get()

        create_folder = partial(Folder.objects.create, user=user)
        folder1 = create_folder(title='Folder#1', description='Folder#1', is_deleted=True)
        create_folder(title='Folder#2', description='Folder#2', parent_folder=folder1)

        self.assertPOST409(folder1.get_delete_absolute_url())
        self.assertStillExists(folder1)

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview__not_deletable01(self):
        "Not deletable folder: 'Docs related to entities'."
        self.login_as_root()
        folder = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_RELATED2ENTITIES)

        self.assertPOST409(folder.get_delete_absolute_url())

    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_deleteview__not_deletable02(self):
        "Not deletable folder: 'Images'."
        self.login_as_root()
        folder = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_IMAGES)

        self.assertPOST409(folder.get_delete_absolute_url())

    def test_bricks(self):
        user = self.login_as_root_and_get()

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

        create_doc = partial(self._create_doc, user=user)
        doc1 = create_doc(title='Test doc #1', folder=folder)
        doc2 = create_doc(title='Test doc #2', folder=folder)
        doc3 = create_doc(title='Test doc #3')
        doc4 = create_doc(title='Test doc #4', folder=folder)

        doc4.trash()

        response = self.assertGET200(folder.get_absolute_url())
        tree = self.get_html_tree(response.content)

        brick_node1 = self.get_brick_node(tree, brick=FolderDocsBrick)
        self.assertInstanceLink(brick_node1, doc1)
        self.assertInstanceLink(brick_node1, doc2)
        self.assertInstanceLink(brick_node1, doc4)  # TODO: see bricks.py
        self.assertNoInstanceLink(brick_node1, doc3)

        brick_node2 = self.get_brick_node(tree, brick=ChildFoldersBrick)
        self.assertInstanceLink(brick_node2, child1)
        self.assertInstanceLink(brick_node2, child2)
        self.assertNoInstanceLink(brick_node2, child3)

    def test_merge01(self):
        user = self.login_as_root_and_get()

        create_folder = partial(Folder.objects.create, user=user)
        folder1 = create_folder(title='Folder#1', description='Folder#1')
        folder2 = create_folder(title='Folder#2', description='Folder#2')
        folder3 = create_folder(title='Folder#3', description='Folder#3')

        create_doc = partial(self._create_doc, user=user)
        doc1 = create_doc(title='Test doc #1', folder=folder1)
        doc2 = create_doc(title='Test doc #2', folder=folder2)

        url = self.build_merge_url(folder1, folder2)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            form = response1.context['form']
            fields = form.fields

        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder2, getattr(form, 'entity2', None))

        self.assertIn('title', fields)
        self.assertNotIn('parent_folder', fields)

        # ---
        response2 = self.client.post(
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
        self.assertNoFormError(response2)

        self.assertDoesNotExist(folder2)

        with self.assertNoException():
            merged_folder = self.refresh(folder1)

        self.assertEqual(folder1.title,       merged_folder.title)
        self.assertEqual(folder2.description, merged_folder.description)
        self.assertIsNone(merged_folder.parent_folder)

        self.assertCountEqual([doc1, doc2], merged_folder.document_set.all())

    def test_merge02(self):
        "One folder is the parent of the other one."
        user = self.login_as_root_and_get()

        create_folder = partial(Folder.objects.create, user=user)
        folder1 = create_folder(title='Folder#1', description='Folder#1')
        folder2 = create_folder(title='Folder#2', description='Folder#2', parent_folder=folder1)
        folder3 = create_folder(title='Folder#3', description='Folder#3', parent_folder=folder2)

        build_url = self.build_merge_url
        response = self.assertGET200(build_url(folder1, folder3))

        form = self.get_form_or_fail(response)
        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder3, getattr(form, 'entity2', None))

        # -------------
        form = self.assertGET200(build_url(folder3, folder1)).context['form']

        # Swapped
        self.assertEqual(folder1, getattr(form, 'entity1', None))
        self.assertEqual(folder3, getattr(form, 'entity2', None))

    def test_merge__one_system_folder(self):
        user = self.login_as_root_and_get()

        folder1 = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_IMAGES)
        folder2 = Folder.objects.create(user=user, title='Not system Folder')

        build_url = self.build_merge_url
        response = self.assertGET200(build_url(folder1, folder2))

        form1 = self.get_form_or_fail(response)
        self.assertEqual(folder1, getattr(form1, 'entity1', None))
        self.assertEqual(folder2, getattr(form1, 'entity2', None))

        # -------------
        form2 = self.assertGET200(build_url(folder2, folder1)).context['form']

        # Swapped
        self.assertEqual(folder1, getattr(form2, 'entity1', None))
        self.assertEqual(folder2, getattr(form2, 'entity2', None))

    def test_merge__two_system_folders(self):
        self.login_as_root()

        folder1 = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_IMAGES)
        folder2 = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_RELATED2ENTITIES)

        response = self.client.get(self.build_merge_url(folder1, folder2))
        self.assertContains(
            response=response,
            text=_('Can not merge 2 system Folders.'),
            status_code=409,
            # html=True,
        )

    def test_merge__child_system_folder(self):
        "The system folder is child of the other one."
        user = self.login_as_root_and_get()

        create_folder = partial(Folder.objects.create, user=user)
        folder1 = create_folder(title='Parent')
        folder2 = create_folder(title='Child', parent_folder=folder1)
        folder3 = create_folder(title='System', parent_folder=folder2)

        try:
            Folder.not_deletable_UUIDs.add(str(folder3.uuid))

            response = self.client.get(self.build_merge_url(folder1, folder3))
            self.assertContains(
                response=response,
                text=_(
                    'Can not merge because a child is a system Folder: {folder}'
                ).format(folder=folder3),
                status_code=409,
                # html=True,
            )

            self.assertGET409(self.build_merge_url(folder3, folder1))
        finally:
            Folder.not_deletable_UUIDs.discard(str(folder3.uuid))

    def test_deletor(self):
        user = self.get_root_user()
        folder1 = Folder.objects.create(user=user, title='Pix')
        deletor = FolderDeletor()

        with self.assertNoException():
            deletor.check_permissions(user=user, entity=folder1)

        # System folder ---
        folder2 = self.get_object_or_fail(Folder, uuid=constants.UUID_FOLDER_IMAGES)

        with self.assertRaises(ConflictError) as cm:
            deletor.check_permissions(user=self.get_root_user(), entity=folder2)

        self.assertEqual(
            _('This folder is a system folder.'),
            str(cm.exception),
        )
