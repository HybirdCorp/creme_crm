import filecmp
from decimal import Decimal
from functools import partial
from io import BytesIO
from os.path import basename, exists, join
from pathlib import Path
from unittest import skipIf
from zipfile import ZipFile

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import filesizeformat
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from PIL.Image import open as open_img

from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.gui import actions
from creme.creme_core.gui.field_printers import field_printer_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CremeEntity,
    FakeOrganisation,
    FileRef,
    HeaderFilter,
    RelationType,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons import get_contact_model
from creme.persons.tests.base import skipIfCustomContact

from ..actions import BulkDownloadAction, DownloadAction
from ..bricks import LinkedDocsBrick
from ..constants import REL_SUB_RELATED_2_DOC, UUID_FOLDER_RELATED2ENTITIES
from ..models import DocumentCategory, FolderCategory, MimeType
from ..utils import get_csv_folder_or_create
from .base import (
    Document,
    Folder,
    _DocumentsTestCase,
    skipIfCustomDocument,
    skipIfCustomFolder,
)

if apps.is_installed('creme.products'):
    from creme.products import product_model_is_custom

    skip_product_test = product_model_is_custom()
else:
    skip_product_test = True


class MimeTypeTestCase(_DocumentsTestCase):
    def test_portable_key(self):
        name = 'image/png'
        mtype = MimeType.objects.get_or_create(name=name)[0]
        self.assertIsInstance(mtype, MimeType)
        self.assertEqual(name, mtype.name)

        with self.assertNoException():
            key = mtype.portable_key()
        self.assertEqual(name, key)

        # ---
        with self.assertNoException():
            got_mtype = MimeType.objects.get_by_portable_key(key)
        self.assertEqual(mtype, got_mtype)

    def test_get_by_portable_key__creation(self):
        name = 'image/heif'
        self.assertFalse(MimeType.objects.filter(name=name).exists())

        with self.assertNoException():
            mtype = MimeType.objects.get_by_portable_key(key=name)
        self.assertIsInstance(mtype, MimeType)
        self.assertEqual(name, mtype.name)


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentTestCase(BrickTestCaseMixin, _DocumentsTestCase):
    @staticmethod
    def _build_addrelated_url(entity):
        return reverse('documents__create_related_document', args=(entity.id,))

    def test_populate(self):
        self.get_object_or_fail(RelationType, pk=REL_SUB_RELATED_2_DOC)

        get_ct = ContentType.objects.get_for_model
        hf_filter = HeaderFilter.objects.filter
        self.assertTrue(hf_filter(entity_type=get_ct(Document)).exists())
        self.assertTrue(hf_filter(entity_type=get_ct(Folder)).exists())

        self.assertTrue(Folder.objects.exists())
        self.assertTrue(FolderCategory.objects.exists())
        self.assertTrue(DocumentCategory.objects.exists())

    def test_create(self):
        "Autofill title if empty."
        from creme.creme_core.utils.file_handling import FileCreator

        filename = 'DocTestCreate001.txt'
        final_path = FileCreator(
            dir_path=join(settings.MEDIA_ROOT, 'documents'),
            name=filename,
            max_length=Document._meta.get_field('filedata').max_length,
        ).create()

        content = 'Hi! I am the content'
        with open(final_path, 'w') as f:
            f.write(content)

        user = self.get_root_user()
        folder = Folder.objects.all()[0]

        title = 'Test doc'
        doc1 = Document.objects.create(
            user=user,
            title=title,
            linked_folder=folder,
            filedata=final_path,
        )
        self.assertEqual(title, doc1.title)

        doc2 = Document.objects.create(
            user=user,
            linked_folder=folder,
            filedata=final_path,
        )
        self.assertEqual(filename, doc2.title)

        size = len(content)
        self.assertEqual(size, doc2.file_size)

        # Field printer ---
        self.assertEqual(
            (
                ngettext('%(size)d byte', '%(size)d bytes', size) % {'size': size}
            ).replace(' ', '\xa0'),
            field_printer_registry.get_field_value(
                instance=doc1,
                field_name='file_size',
                user=user,
                tag=ViewTag.HTML_DETAIL,
            ),
        )

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'pdf'))
    def test_creation_view(self):
        user = self.login_as_root_and_get()

        self.assertFalse(Document.objects.exists())

        url = self.ADD_DOC_URL
        self.assertGET200(url)

        ext = settings.ALLOWED_EXTENSIONS[0]

        create_cat = DocumentCategory.objects.create
        cat1 = create_cat(name='Text')
        cat2 = create_cat(name='No image')

        title = 'Test doc'
        description = 'Test description'
        content = 'Yes I am the content (DocumentTestCase.test_createview)'
        file_obj = self.build_filedata(content, suffix=f'.{ext}')
        folder = Folder.objects.all()[0]
        response = self.client.post(
            self.ADD_DOC_URL,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'filedata':      file_obj,
                'linked_folder': folder.id,
                'description':   description,
                'categories':    [cat1.id, cat2.id],
            },
        )
        self.assertNoFormError(response)

        doc = self.get_alone_element(Document.objects.all())
        self.assertEqual(title,        doc.title)
        self.assertEqual(description,  doc.description)
        self.assertEqual(folder,       doc.linked_folder)
        self.assertEqual(len(content), doc.file_size)
        self.assertIsNotNone(doc.mime_type)
        self.assertCountEqual([cat1, cat2], [*doc.categories.all()])

        self.assertRedirects(response, doc.get_absolute_url())

        filedata = doc.filedata
        self.assertEqual(Path('documents/' + file_obj.base_name), Path(filedata.name))
        with filedata.open('r') as f:
            self.assertEqual([content], f.readlines())

        # Download
        response = self.assertGET200(doc.get_download_absolute_url())
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            f'attachment; filename="{file_obj.base_name}"',
            response['Content-Disposition'],
        )

        # Avoid <ResourceWarning: unclosed file...>
        b''.join(response.streaming_content)

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'png', 'py'))
    def test_creation_view__forbidden_extension(self):
        user = self.login_as_root_and_get()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        file_obj = self.build_filedata('Content', suffix='.' + ext)
        doc = self._create_doc(title, file_obj=file_obj, user=user)

        filedata = doc.filedata

        self.assertEqual(Path(f'documents/{file_obj.base_name}.txt'), Path(filedata.name))

        # Download
        response = self.assertGET200(doc.get_download_absolute_url())
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            f'attachment; filename="{file_obj.base_name}.txt"',
            response['Content-Disposition'],
        )

        # Avoid <ResourceWarning: unclosed file...>
        b''.join(response.streaming_content)

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'png', 'py'))
    def test_creation_view__double_extension(self):
        "Double extension (bugfix)."
        user = self.login_as_root_and_get()

        ext = 'php'
        self.assertNotIn(ext, settings.ALLOWED_EXTENSIONS)

        title = 'My doc'
        file_obj = self.build_filedata('Content', suffix='.old.' + ext)
        doc = self._create_doc(title=title, file_obj=file_obj, user=user)

        filedata = doc.filedata
        self.assertEqual(Path(f'documents/{file_obj.base_name}.txt'), Path(filedata.name))

        # Download
        response = self.assertGET200(doc.get_download_absolute_url())
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            f'attachment; filename="{file_obj.base_name}.txt"',
            response['Content-Disposition'],
        )

        # Avoid <ResourceWarning: unclosed file...>
        b''.join(response.streaming_content)

    def test_creation_view__no_extension(self):
        user = self.login_as_root_and_get()

        title = 'My doc'
        file_obj = self.build_filedata('Content', suffix='')
        doc = self._create_doc(title=title, file_obj=file_obj, user=user)

        filedata = doc.filedata
        self.assertEqual(Path(f'documents/{file_obj.base_name}.txt'), Path(filedata.name))

        # Download
        response = self.assertGET200(doc.get_download_absolute_url())
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            f'attachment; filename="{file_obj.base_name}.txt"',
            response['Content-Disposition'],
        )

        # Avoid <ResourceWarning: unclosed file...>
        b''.join(response.streaming_content)

    def test_creation_view__no_title(self):
        user = self.login_as_root_and_get()

        ext = settings.ALLOWED_EXTENSIONS[0]
        file_obj = self.build_filedata('Content', suffix='.' + ext)

        folder = Folder.objects.create(user=user, title='test_createview05')
        response = self.client.post(
            self.ADD_DOC_URL, follow=True,
            data={
                'user':          user.pk,
                # 'title':       '',
                'filedata':      file_obj,
                'linked_folder': folder.id,
            },
        )

        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, linked_folder=folder)
        file_name = file_obj.base_name
        self.assertEqual(Path(f'documents/{file_name}'), Path(doc.filedata.name))

        self.assertEqual(file_name, doc.title)

    @override_settings(ALLOWED_EXTENSIONS=('txt', 'png'))
    def test_creation_view__uppercase_extension(self):
        "Uploaded image + upper-case extension (bugfix)."
        user = self.login_as_root_and_get()

        with open(
            join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png'),
            'rb',
        ) as image_file:
            file_obj = self.build_filedata(image_file.read(), suffix='.PNG')

        doc = self._create_doc(title='My image', file_obj=file_obj, user=user)
        self.assertEqual('image/png', doc.mime_type.name)

        filedata = doc.filedata

        name_parts = filedata.name.split('.')
        self.assertEqual(2, len(name_parts))
        self.assertEqual('PNG', name_parts[-1])

        with self.assertNoException():
            with open_img(filedata.path) as img_fd:
                size = img_fd.size

        self.assertTupleEqual((22, 22), size)

    def test_detail_view(self):
        user = self.login_as_root_and_get()

        create_cat = DocumentCategory.objects.create
        cat1 = create_cat(name='Text')
        cat2 = create_cat(name='No image')

        doc = self._create_doc(user=user, title='Test doc', categories=[cat1.id, cat2.id])

        response = self.assertGET200(doc.get_absolute_url())
        self.assertTemplateUsed(response, 'documents/bricks/document-hat-bar.html')

        brick_node = self.get_brick_node(self.get_html_tree(response.content), MODELBRICK_ID)
        self.assertEqual(
            _('Information on the document'),
            self.get_brick_title(brick_node),
        )
        self.assertEqual(
            doc.title,
            self.get_brick_tile(brick_node, 'regular_field-title').text,
        )
        self.assertCountEqual(
            [cat1.name, cat2.name],
            [
                n.text
                for n in self.get_brick_tile(brick_node, 'regular_field-categories')
                             .findall('.//li')
            ],
        )

    def test_edition_view(self):
        user = self.login_as_root_and_get()

        title = 'Test doc'
        description = 'Test description'
        content = 'Yes I am the content (DocumentTestCase.test_edition_view)'
        doc = self._create_doc(
            user=user,
            title=title,
            file_obj=self.build_filedata(content),
            description=description,
        )

        url = doc.get_edit_absolute_url()
        self.assertGET200(url)

        title = title.upper()
        description = description.upper()
        # content     = content.upper() TODO: use ?
        folder = Folder.objects.create(
            title='Test folder',
            parent_folder=None,
            category=FolderCategory.objects.all()[0],
            user=user,
        )

        response = self.client.post(
            url,
            follow=True,
            data={
                'user':          user.pk,
                'title':         title,
                'description':   description,
                'linked_folder': folder.id,
            },
        )
        self.assertNoFormError(response)

        doc = self.refresh(doc)
        self.assertEqual(title,       doc.title)
        self.assertEqual(description, doc.description)
        self.assertEqual(folder,      doc.linked_folder)

        self.assertRedirects(response, doc.get_absolute_url())

    def test_add_related_document(self):
        user = self.login_as_root_and_get()
        root_folder = self.get_object_or_fail(Folder, uuid=UUID_FOLDER_RELATED2ENTITIES)

        Folder.objects.create(user=user, title=root_folder.title)  # Should not be used

        entity = FakeOrganisation.objects.create(user=user, name='NERV')
        url = self._build_addrelated_url(entity)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('New document for «{entity}»').format(entity=entity),
            context.get('title'),
        )
        self.assertEqual(Document.save_label, context.get('submit_label'))

        def post(title):
            response = self.client.post(
                url, follow=True,
                data={
                    'user': user.id,
                    'title': title,
                    'description': 'Test description',
                    'filedata': self.build_filedata(
                        'Yes I am the content (DocumentTestCase.test_add_related_document01)'
                    ),
                },
            )
            self.assertNoFormError(response)

            return self.get_object_or_fail(Document, title=title)

        doc1 = post('Related doc')
        self.assertHaveRelation(subject=entity, type=REL_SUB_RELATED_2_DOC, object=doc1)

        entity_folder = doc1.linked_folder
        self.assertIsNotNone(entity_folder)
        self.assertEqual(f'{entity.id}_{entity}', entity_folder.title)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(str(FakeOrganisation._meta.verbose_name), ct_folder.title)
        self.assertEqual(root_folder, ct_folder.parent_folder)

        doc2 = post('Related doc #2')
        entity_folder2 = doc2.linked_folder
        self.assertEqual(entity_folder, entity_folder2)
        self.assertEqual(ct_folder,     entity_folder2.parent_folder)

        # ---
        LinkedDocsBrick.page_size = max(4, settings.BLOCK_SIZE)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=LinkedDocsBrick,
            model=type(entity),
            order=50,
            zone=BrickDetailviewLocation.RIGHT,
        )

        response = self.assertGET200(entity.get_absolute_url())
        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, brick=LinkedDocsBrick)
        self.assertInstanceLink(brick_node, doc1)
        self.assertInstanceLink(brick_node, doc2)

    def test_add_related_document__creation_perms(self):
        "Creation credentials."
        user = self.login_as_standard(allowed_apps=['documents', 'creme_core'])
        self.add_credentials(user.role, all='*')

        entity = CremeEntity.objects.create(user=user)
        self.assertGET403(self._build_addrelated_url(entity))

    def test_add_related_document__link_perms(self):
        "Link credentials."
        user = self.login_as_standard(
            allowed_apps=['documents', 'creme_core'],
            creatable_models=[Document],
        )
        self.add_credentials(user.role, own='!LINK')

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._build_addrelated_url(orga)
        self.assertGET403(url)

        self.add_credentials(user.role, own=['LINK'], model=FakeOrganisation)
        self.assertGET403(url)

        self.add_credentials(user.role, own=['LINK'], model=Document)
        self.assertGET200(url)

        # A named variable to close it cleanly
        file_obj = self.build_filedata(
            'Yes I am the content (DocumentTestCase.test_add_related_document03)'
        )
        response = self.assertPOST200(
            url, follow=True,
            data={
                'user': self.get_root_user().pk,
                'title': 'Title',
                'description': 'Test description',
                'filedata': file_obj,
            }
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='user',
            errors=_('You are not allowed to link with the «{models}» of this user.').format(
                models=_('Documents'),
            ),
        )

    def test_add_related_document__link_perms_on_related(self):
        "Link credentials with related entity are needed."
        user = self.login_as_standard(
            allowed_apps=['documents', 'creme_core'],
            creatable_models=[Document],
        )
        self.add_credentials(user.role, own='!LINK')
        self.add_credentials(user.role, own='*', model=Document)

        orga = FakeOrganisation.objects.create(user=user, name='NERV')
        self.assertTrue(user.has_perm_to_view(orga))
        self.assertFalse(user.has_perm_to_link(orga))

        url = self._build_addrelated_url(orga)
        self.assertGET403(url)

    def test_add_related_document__view_perms(self):
        "View credentials."
        user = self.login_as_standard(
            allowed_apps=['documents', 'creme_core'],
            creatable_models=[Document],
        )
        self.add_credentials(user.role, all='!VIEW')

        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='NERV')
        self.assertTrue(user.has_perm_to_link(orga))
        self.assertFalse(user.has_perm_to_view(orga))
        self.assertGET403(self._build_addrelated_url(orga))

    def test_add_related_document__long_folder_name(self):
        "The Folder containing all the Documents related to the entity has a too long name."
        user = self.login_as_root_and_get()

        MAX_LEN = 100
        self.assertEqual(MAX_LEN, Folder._meta.get_field('title').max_length)

        with self.assertNoException():
            entity = FakeOrganisation.objects.create(user=user, name='A' * MAX_LEN)

        self.assertEqual(100, len(str(entity)))

        title = 'Related doc'
        response = self.client.post(
            self._build_addrelated_url(entity),
            follow=True,
            data={
                'user': user.id,
                'title': title,
                'description': 'Test description',
                'filedata': self.build_filedata(
                    'Yes I am the content (DocumentTestCase.test_add_related_document05)'
                ),
            },
        )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)
        entity_folder = doc.linked_folder
        self.assertIsNotNone(entity_folder)

        title = entity_folder.title
        self.assertEqual(100, len(title))
        self.assertStartsWith(title, f'{entity.id}_AAAAAAA')
        self.assertEndsWith(title, '…')

    def test_add_related_document__folder_name_collision(self):
        "Collision with Folder titles."
        user = self.login_as_root_and_get()
        entity = CremeEntity.objects.create(user=user)
        root_folder = self.get_object_or_fail(Folder, uuid=UUID_FOLDER_RELATED2ENTITIES)

        # NB: collision with folders created by the view
        create_folder = partial(Folder.objects.create, user=user)
        my_ct_folder = create_folder(title=str(entity.entity_type))
        my_entity_folder = create_folder(title=f'{entity.id}_{entity}')

        title = 'Related doc'
        response = self.client.post(
            self._build_addrelated_url(entity),
            follow=True,
            data={
                'user':         user.pk,
                'title':        title,
                'description':  'Test description',
                'filedata':     self.build_filedata(
                    'Yes I am the content '
                    '(DocumentTestCase.test_add_related_document06)'
                ),
            },
        )
        self.assertNoFormError(response)

        doc = self.get_object_or_fail(Document, title=title)

        entity_folder = doc.linked_folder
        self.assertEqual(my_entity_folder.title, entity_folder.title)
        self.assertNotEqual(my_entity_folder, entity_folder)

        ct_folder = entity_folder.parent_folder
        self.assertIsNotNone(ct_folder)
        self.assertEqual(my_ct_folder.title, ct_folder.title)
        self.assertNotEqual(my_ct_folder, ct_folder)

        self.assertEqual(root_folder, ct_folder.parent_folder)

    def test_listview(self):
        user = self.login_as_root_and_get()

        create_doc = partial(self._create_doc, user=user)
        doc1 = create_doc(title='Test doc #1')
        doc2 = create_doc(title='Test doc #2')

        response = self.assertGET200(Document.get_lv_absolute_url())

        with self.assertNoException():
            docs = response.context['page_obj'].object_list

        self.assertIn(doc1, docs)
        self.assertIn(doc2, docs)

    def test_listview_actions(self):
        user = self.login_as_root_and_get()
        doc1 = self._create_doc(user=user, title='Test doc #1')

        download_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=doc1)
            if isinstance(action, DownloadAction)
        )
        self.assertEqual('redirect', download_action.type)
        self.assertEqual(
            doc1.get_download_absolute_url(),
            download_action.url,
        )
        self.assertTrue(download_action.is_enabled)
        self.assertTrue(download_action.is_visible)

    @override_settings(DOCUMENTS_BULK_DOWNLOAD_MAX_SIZE=1_000)
    def test_bulk_download(self):
        user = self.login_as_standard(
            allowed_apps=['documents'], creatable_models=[Document],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        existing_file_ref_ids = [*FileRef.objects.values_list('id', flat=True)]

        folder = Folder.objects.create(user=user, title='My docs')
        content1 = 'Doc1:\n The content which is so interesting'
        file_obj1 = self.build_filedata(content1)
        doc1 = self._create_doc(user=user, title='Doc #1', folder=folder, file_obj=file_obj1)
        doc2 = self._create_doc(user=user, title='Doc #2', folder=folder)
        self._create_doc(user=user, title='Doc #3', folder=folder)

        response = self.assertGET200(
            reverse('documents__bulk_download'),
            follow=True,
            data={'id': [doc1.id, doc2.id]},
        )
        self.assertEqual('application/zip', response['Content-Type'])

        with self.assertNoException():
            zip_file = ZipFile(BytesIO(b''.join(response.streaming_content)))

        name1 = basename(doc1.filedata.path)
        self.assertCountEqual(
            [name1, basename(doc2.filedata.path)], zip_file.namelist(),
        )

        with self.assertNoException():
            with zip_file.open(name1) as doc_file1:
                self.assertEqual(content1.encode(), doc_file1.read())

        file_ref = self.get_alone_element(
            FileRef.objects.exclude(id__in=existing_file_ref_ids)
        )
        self.assertEqual(user, file_ref.user)

        verbose_name = _('Documents')
        self.assertEqual(f'{verbose_name}_X2.zip', file_ref.basename)
        self.assertEqual(
            _('Bulk download of {count} {model}').format(count=2, model=verbose_name),
            file_ref.description,
        )

    def test_bulk_download__ids_errors(self):
        self.login_as_root()
        url = reverse('documents__bulk_download')

        # Empty ---
        response1 = self.client.get(
            url, follow=True,  # data={'id': [...]},
        )
        self.assertContains(response1, 'The list of IDs is empty', status_code=409)

        # Bad type ---
        response3 = self.client.get(
            url, follow=True, data={'id': [12, 'not_int', 14]},
        )
        self.assertContains(response3, 'Some IDs are invalid', status_code=409)

    def test_bulk_download__app_perms(self):
        user = self.login_as_standard(allowed_apps=['persons'])  # 'documents'
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        response = self.client.get(
            reverse('documents__bulk_download'), follow=True, data={'id': [12, 14]},
        )
        self.assertContains(
            response,
            _('You are not allowed to access to the app: {}').format(_('Documents')),
            status_code=403, html=True,
        )

    def test_bulk_download__view_perms(self):
        user = self.login_as_standard(
            allowed_apps=['documents'],
            creatable_models=[Document],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        folder = Folder.objects.create(user=user, title='My docs')
        doc1 = self._create_doc(user=user, title='Doc #1', folder=folder)
        doc2 = self._create_doc(user=user, title='Doc #2', folder=folder)

        doc2.user = self.get_root_user()
        doc2.save()

        response = self.client.get(
            reverse('documents__bulk_download'),
            follow=True, data={'id': [doc1.id, doc2.id]},
        )
        self.assertContains(
            response,
            _('Some documents are invalid or not viewable'),
            status_code=403,
        )

    @override_settings(DOCUMENTS_BULK_DOWNLOAD_MAX_SIZE=100)
    def test_bulk_download__size_limit(self):
        user = self.login_as_root_and_get()

        content1 = 'Doc1:\n the content which is so interesting, but which will be too big.'
        content2 = 'Doc2:\n this content is very very very interesting too (or not)'
        self.assertGreater(len(content1) + len(content2), 100)

        file_obj1 = self.build_filedata(content1)
        file_obj2 = self.build_filedata(content2)
        doc1 = self._create_doc(user=user, title='Doc #1', file_obj=file_obj1)
        doc2 = self._create_doc(user=user, title='Doc #2', file_obj=file_obj2)

        response = self.client.get(
            reverse('documents__bulk_download'),
            follow=True,
            data={'id': [doc1.id, doc2.id]},
        )
        self.assertContains(
            response,
            _(
                'The total size of these files is {size} which is greater than '
                'the allowed limit ({limit}).'
            ).format(
                size=filesizeformat(132),
                limit=filesizeformat(100),
            ),
            status_code=409,
        )

    def test_bulk_download_action(self):
        self.assertIn(
            BulkDownloadAction,
            actions.action_registry.bulk_action_classes(model=Document),
        )

        self.assertEqual('documents-bulk_download', BulkDownloadAction.id)
        self.assertEqual(Document,                  BulkDownloadAction.model)
        self.assertEqual(1,                         BulkDownloadAction.bulk_min_count)
        self.assertEqual(_('Download as .zip'),     BulkDownloadAction.label)
        self.assertEqual(
            reverse('documents__bulk_download'),
            BulkDownloadAction(user=self.get_root_user()).url,
        )

    def test_delete_category(self):
        "Set to null."
        user = self.login_as_root_and_get()

        cat = FolderCategory.objects.create(name='Manga')
        folder = Folder.objects.create(user=user, title='One piece', category=cat)

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('documents', 'category', cat.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(FolderCategory).job
        job.type.execute(job)
        self.assertDoesNotExist(cat)

        folder = self.assertStillExists(folder)
        self.assertIsNone(folder.category)

    @skipIfCustomContact
    def test_field_printers__fk__image(self):
        "Field printer with FK on Image."
        user = self.login_as_root_and_get()

        image = self._create_image(user=user)
        summary = image.get_entity_summary(user)
        self.assertHTMLEqual(
            '<img class="entity-summary" src="{url}" alt="{name}" title="{name}"/>'.format(
                url=image.get_download_absolute_url(),
                name=image.title,
            ),
            summary,
        )

        casca = get_contact_model().objects.create(
            user=user,
            image=image,
            first_name='Casca', last_name='Mylove',
        )
        self.assertHTMLEqual(
            f'''<a onclick="creme.dialogs.image('{image.get_download_absolute_url()}').open();">'''
            f'''{summary}'''
            f'''</a>''',
            field_printer_registry.get_field_value(
                instance=casca, field_name='image', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )
        self.assertEqual(
            str(casca.image),
            field_printer_registry.get_field_value(
                instance=casca, field_name='image', user=user, tag=ViewTag.TEXT_PLAIN,
            ),
        )

    @skipIfCustomContact
    def test_field_printers__fk__image__perms(self):
        "Field printer with FK on Image + credentials."
        Contact = get_contact_model()

        user = self.login_as_root_and_get()
        role = self.create_role(
            allowed_apps=['creme_core', 'persons', 'documents'],
            exportable_models=[Contact],
        )
        other_user = self.create_user(role=role)

        self.add_credentials(role, own='*')

        create_img = self._create_image
        casca_face = create_img(title='Casca face', user=user,       description="Casca's selfie")
        judo_face  = create_img(title='Judo face',  user=other_user, description="Judo's selfie")

        self.assertTrue(other_user.has_perm_to_view(judo_face))
        self.assertFalse(other_user.has_perm_to_view(casca_face))

        create_contact = partial(Contact.objects.create, user=other_user)
        casca = create_contact(first_name='Casca', last_name='Mylove', image=casca_face)
        judo  = create_contact(first_name='Judo',  last_name='Doe',    image=judo_face)

        render_field = partial(
            field_printer_registry.get_field_value,
            user=other_user,
            tag=ViewTag.HTML_DETAIL,
        )
        url = judo_face.get_download_absolute_url()
        self.assertHTMLEqual(
            f'''<a onclick="creme.dialogs.image('{url}').open();">
                {judo_face.get_entity_summary(other_user)}
            </a>
            ''',
            render_field(instance=judo, field_name='image'),
        )
        self.assertEqual(
            '<p>Judo&#x27;s selfie</p>',
            render_field(instance=judo, field_name='image__description'),
        )

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(HIDDEN_VALUE, render_field(instance=casca, field_name='image'))
        self.assertEqual(
            HIDDEN_VALUE, render_field(instance=casca, field_name='image__description'),
        )

    @skipIfCustomContact
    def test_field_printers__fk__not_image(self):
        "Document is not an Image."
        user = self.login_as_root_and_get()

        doc = self._create_doc(user=user, title='Text doc')
        contact = get_contact_model().objects.create(
            user=user, image=doc, first_name='Casca', last_name='Mylove',
        )
        self.assertHTMLEqual(
            f'<a href="{doc.get_absolute_url()}" target="_self">{doc}</a>',
            field_printer_registry.get_field_value(
                instance=contact, field_name='image', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )

    @skipIf(skip_product_test, '"Product" model is not available.')
    @override_settings(HIDDEN_VALUE='XXX', CELL_SIZE=20)
    def test_field_printers__m2m(self):
        "Field printer with M2M on Image."
        from creme.products import get_product_model
        from creme.products.models import SubCategory

        user = self.login_as_standard(
            allowed_apps=('documents', 'products'),
            creatable_models=[Document],
        )
        self.add_credentials(user.role, own=['VIEW', 'CHANGE', 'LINK'])

        folder = Folder.objects.create(user=user, title='My docs')
        image = self._create_image(user=user, ident=1, title='Doc #1', folder=folder)
        doc = self._create_doc(user=user, title='Doc #2', folder=folder)

        forbidden = self._create_doc(user=user, title='Doc #3', folder=folder)
        forbidden.user = self.get_root_user()
        forbidden.save()

        sub_cat = SubCategory.objects.first()
        product = get_product_model().objects.create(
            user=user,
            name='My product',
            category=sub_cat.category,
            sub_category=sub_cat,
            unit_price=Decimal('10'),
        )
        product.images.set([image, doc, forbidden])

        self.assertHTMLEqual(
            f'''<ul class="limited-list">
             <li>
              <a onclick="creme.dialogs.image('{image.get_download_absolute_url()}').open();">
               {image.get_entity_summary(user)}
              </a>
             </li>
             <li><a href="{doc.get_absolute_url()}" target="_blank">{doc}</a></li>
             <li>XXX</li>
            </ul>''',
            field_printer_registry.get_field_value(
                instance=product, field_name='images', user=user, tag=ViewTag.HTML_DETAIL,
            ),
        )


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentQuickFormTestCase(_DocumentsTestCase):
    @staticmethod
    def quickform_data(count):
        return {
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'form-TOTAL_FORMS':   str(count),
        }

    @staticmethod
    def quickform_data_append(data, id, user='', filedata='', folder_id=''):
        return data.update({
            f'form-{id}-user':          user,
            f'form-{id}-filedata':      filedata,
            f'form-{id}-linked_folder': folder_id,
        })

    def test_create(self):
        user = self.login_as_root_and_get()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = reverse(
            'creme_core__quick_form',
            args=(ContentType.objects.get_for_model(Document).id,),
        )
        self.assertGET200(url)

        # ---
        content = 'Yes I am the content (DocumentQuickFormTestCase.test_create)'
        file_obj = self.build_filedata(content)
        folder = Folder.objects.all()[0]
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={
                'user':          user.id,
                'filedata':      file_obj,
                'linked_folder': folder.id,
            },
        ))

        doc = self.get_alone_element(Document.objects.all())
        self.assertEqual(Path('documents/' + file_obj.base_name), Path(doc.filedata.name))
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.linked_folder)

        with doc.filedata.open('r') as f:
            self.assertEqual([content], f.readlines())


@skipIfCustomDocument
@skipIfCustomFolder
class DocumentQuickWidgetTestCase(_DocumentsTestCase):
    def test_add_csv_doc(self):
        user = self.login_as_root_and_get()

        self.assertFalse(Document.objects.exists())
        self.assertTrue(Folder.objects.exists())

        url = reverse('documents__create_document_from_widget')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(_('Create a document'), context.get('title'))
        self.assertEqual(_('Save the document'), context.get('submit_label'))

        # ---
        content = 'Content (DocumentQuickWidgetTestCase.test_add_csv_doc)'
        file_obj = self.build_filedata(content)
        response = self.client.post(
            url, follow=True,
            data={
                'user':     user.pk,
                'filedata': file_obj,
            },
        )
        self.assertNoFormError(response)

        doc = self.get_alone_element(Document.objects.all())
        folder = get_csv_folder_or_create(user)
        self.assertEqual(Path('documents/' + file_obj.base_name), Path(doc.filedata.name))
        self.assertEqual('', doc.description)
        self.assertEqual(folder, doc.linked_folder)

        self.assertDictEqual(
            {
                'added': [[doc.id, str(doc)]],
                'value': doc.id,
            },
            response.json(),
        )

        with doc.filedata.open('r') as f:
            self.assertEqual([content], f.readlines())

    def test_add_csv_doc__regular_user(self):
        self.login_as_standard(allowed_apps=['documents'], creatable_models=[Document])
        self.assertGET200(reverse('documents__create_document_from_widget'))

    def test_add_csv_doc__creation_perms(self):
        "Creation permission needed."
        self.login_as_standard(allowed_apps=['documents'])
        self.assertGET403(reverse('documents__create_document_from_widget'))

    @override_settings(ALLOWED_EXTENSIONS=('png', 'pdf'))
    def test_add_image_doc(self):
        user = self.login_as_root_and_get()

        url = reverse('documents__create_image_popup')
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/form/add-popup.html')

        context = response.context
        self.assertEqual(_('Create an image'), context.get('title'))
        self.assertEqual(_('Save the image'),  context.get('submit_label'))

        # ---
        path = join(settings.CREME_ROOT, 'static', 'chantilly', 'images', 'creme_22.png')
        self.assertTrue(exists(path))

        folder = Folder.objects.all()[0]
        with open(path, 'rb') as image_file:
            response = self.client.post(
                url, follow=True,
                data={
                    'user':   user.pk,
                    'image':  image_file,
                    'linked_folder': folder.id,
                },
            )
        self.assertNoFormError(response)

        doc = self.get_alone_element(Document.objects.all())
        title = doc.title
        self.assertStartsWith(title, 'creme_22')
        self.assertEndsWith(title, '.png')

        self.assertEqual('',         doc.description)
        self.assertEqual(folder,     doc.linked_folder)
        self.assertTrue('image/png', doc.mime_type.name)

        self.assertTrue(filecmp.cmp(path, doc.filedata.path))

        self.assertDictEqual(
            {
                'added': [[doc.id, str(doc)]],
                'value': doc.id,
            },
            response.json(),
        )

    @override_settings(ALLOWED_EXTENSIONS=('png', 'pdf'))
    def test_add_image_doc__not_image_file(self):
        user = self.login_as_root_and_get()

        folder = Folder.objects.all()[0]
        content = '<xml>Content (DocumentQuickWidgetTestCase.test_add_image_doc02)</xml>'
        file_obj = self.build_filedata(content, suffix='.xml')
        response = self.assertPOST200(
            reverse('documents__create_image_popup'),
            follow=True,
            data={
                'user':   user.pk,
                'image':  file_obj,
                'linked_folder': folder.id,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='image',
            errors=_(
                'Upload a valid image. '
                'The file you uploaded was either not an image or a corrupted image.'
            ),
        )
