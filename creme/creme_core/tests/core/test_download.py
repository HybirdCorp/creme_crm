from os.path import basename, join

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, PermissionDenied

from creme.creme_core.core.download import FileFieldDownLoadRegistry
from creme.creme_core.models import (
    FakeDocument,
    FakeFileComponent,
    FakeFolder,
    FakeImage,
    FieldsConfig,
    FileRef,
)
from creme.creme_core.utils.file_handling import FileCreator

from ..base import CremeTestCase


class DownloadTestCase(CremeTestCase):
    # TODO: factorise
    @staticmethod
    def _create_file_for_tempfile(name):
        rel_media_dir_path = 'creme_core-tests'
        abs_path = FileCreator(
            dir_path=join(settings.MEDIA_ROOT, rel_media_dir_path),
            name=name,
        ).create()

        with open(abs_path, 'w') as f:
            f.write('I am the content')

        return abs_path, join(rel_media_dir_path, basename(abs_path))

    def test_filefield_download(self):
        user = self.get_root_user()

        abs_path, rel_path = self._create_file_for_tempfile(
            'DownloadTestCase_test_filefield_download01.txt'
        )
        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=user,
            title='Selfie with RedTail',
            linked_folder=folder,
            filedata=rel_path,
        )

        ffd_registry = FileFieldDownLoadRegistry()

        with self.assertRaises(FileFieldDownLoadRegistry.InvalidField):
            ffd_registry.get(user=user, instance=doc, field_name='filedata')

        ffd_registry.register(model=FakeDocument, field_name='filedata')

        with self.assertNoException():
            dl_filefield = ffd_registry.get(
                user=user, instance=doc, field_name='filedata',
            )

        self.assertEqual(
            FakeDocument._meta.get_field('filedata'),
            dl_filefield.field,
        )
        self.assertEqual(basename(abs_path), dl_filefield.base_name)
        self.assertEqual(abs_path, dl_filefield.file.path)

        # Double registration
        with self.assertRaises(FileFieldDownLoadRegistry.RegistrationError):
            ffd_registry.register(model=FakeDocument, field_name='filedata')

    def test_filefield_download__invalid_field(self):
        "Invalid field at registration."
        ffd_registry = FileFieldDownLoadRegistry()

        with self.assertRaises(FieldDoesNotExist):
            ffd_registry.register(model=FakeDocument, field_name='unknown')

        with self.assertRaises(FileFieldDownLoadRegistry.InvalidField):
            ffd_registry.register(model=FakeDocument, field_name='title')

    def test_filefield_download__credentials(self):
        "Entity credentials."
        user = self.login_as_standard()
        super_user = self.get_root_user()

        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=super_user,
            title='Selfie with RedTail',
            linked_folder=folder,
        )

        self.assertFalse(user.has_perm_to_view(doc))

        ffd_registry = FileFieldDownLoadRegistry().register(
            model=FakeDocument, field_name='filedata',
        )

        with self.assertRaises(PermissionDenied):
            ffd_registry.get(user=user, instance=doc, field_name='filedata')

    def test_filefield_download__unregister(self):
        "Unregister + multi register + not CremeEntity."
        user = self.get_root_user()

        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=user,
            title='Selfie with RedTail',
            linked_folder=folder,
        )

        fcomp = FakeFileComponent.objects.create()

        ffd_registry = FileFieldDownLoadRegistry().register(
            model=FakeDocument, field_name='filedata',
        ).register(
            model=FakeFileComponent, field_name='filedata',
        )

        with self.assertNoException():
            ffd_registry.get(user=user, instance=doc, field_name='filedata')

        with self.assertNoException():
            ffd_registry.get(user=user, instance=fcomp, field_name='filedata')

        ffd_registry.unregister(FakeDocument, 'filedata')

        with self.assertNoException():
            dl_filefield = ffd_registry.get(
                user=user, instance=fcomp, field_name='filedata',
            )

        self.assertEqual(
            dl_filefield.field,
            FakeFileComponent._meta.get_field('filedata')
        )

        with self.assertRaises(FileFieldDownLoadRegistry.InvalidField):
            ffd_registry.get(user=user, instance=doc, field_name='filedata')

        # Unregister twice ------
        with self.assertNoException():
            ffd_registry.unregister(FakeDocument, 'filedata')

        # Unregister model not registered ------
        with self.assertNoException():
            ffd_registry.unregister(FakeImage, 'filedata')

    def test_filefield_download__default_perm_checker(self):
        "Not CremeEntity + credentials."
        user = self.login_as_standard(allowed_apps=('documents',))

        fcomp = FakeFileComponent.objects.create()

        ffd_registry = FileFieldDownLoadRegistry().register(
            model=FakeFileComponent, field_name='filedata',
        )

        with self.assertRaises(PermissionDenied):
            ffd_registry.get(user=user, instance=fcomp, field_name='filedata')

    def test_filefield_download__fieldsconfig(self):
        "FieldsConfig."
        user = self.get_root_user()

        FieldsConfig.objects.create(
            content_type=FakeDocument,
            descriptions=[('filedata', {FieldsConfig.HIDDEN: True})],
        )

        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=user,
            title='Selfie with RedTail',
            linked_folder=folder,
        )

        ffd_registry = FileFieldDownLoadRegistry().register(
            model=FakeDocument, field_name='filedata',
        )

        with self.assertRaises(FileFieldDownLoadRegistry.InvalidField):
            ffd_registry.get(user=user, instance=doc, field_name='filedata')

    def test_filefield_download__fileref(self):
        "FileRef."
        user = self.get_root_user()

        temp_file = FileRef.objects.create(
            user=user,
            filedata=self._create_file_for_tempfile(
                'DownloadTestCase_test_filefield_download07.txt'
            )[1],
        )

        ffd_registry = FileFieldDownLoadRegistry().register(
            model=FileRef, field_name='filedata',
        )

        with self.assertNoException():
            ffd_registry.get(user=user, instance=temp_file, field_name='filedata')

    def test_filefield_download__fileref_perm(self):
        "TempFile belongs to another user."
        user = self.get_root_user()
        temp_file = FileRef.objects.create(
            user=self.create_user(0),
            filedata=self._create_file_for_tempfile(
                'DownloadTestCase_test_filefield_download08.txt'
            )[1],
        )

        ffd_registry = FileFieldDownLoadRegistry().register(
            model=FileRef, field_name='filedata',
        )

        with self.assertRaises(PermissionDenied):
            ffd_registry.get(user=user, instance=temp_file, field_name='filedata')

        # Staff user ---
        staff = self.create_user(index=1, is_staff=True)

        with self.assertNoException():
            ffd_registry.get(user=staff, instance=temp_file, field_name='filedata')

    def test_filefield_download__custom_perm(self):
        "Custom permission check."
        user = self.get_root_user()
        temp_file = FileRef.objects.create(
            user=None,
            filedata=self._create_file_for_tempfile(
                'DownloadTestCase_test_filefield_download09.txt'
            )[1],
        )

        args = []

        def p_handler(user, instance):
            args.append((user, instance))

        ffd_registry = FileFieldDownLoadRegistry()
        ffd_registry.register(
            model=FileRef,
            field_name='filedata',
            permission_checker=p_handler,
        )

        with self.assertNoException():
            ffd_registry.get(user=user, instance=temp_file, field_name='filedata')

        self.assertListEqual([(user, temp_file)], args)

    def test_filefield_download__basename(self):
        "Basename."
        user = self.get_root_user()
        abs_path, rel_path = self._create_file_for_tempfile(
            'DownloadTestCase_test_filefield_download10.txt'
        )
        temp_file = FileRef.objects.create(user=user, filedata=rel_path)

        args = []
        basename = 'Foobar'

        def b_handler(instance, field, file_obj):
            args.append((instance, field, file_obj))
            return basename

        ffd_registry = FileFieldDownLoadRegistry()
        ffd_registry.register(
            model=FileRef,
            field_name='filedata',
            basename_builder=b_handler,
        )

        with self.assertNoException():
            dl_filefield = ffd_registry.get(
                user=user, instance=temp_file, field_name='filedata',
            )

        self.assertEqual(1, len(args))

        arg_tuple = args[0]
        self.assertEqual(temp_file, arg_tuple[0])
        self.assertEqual(FileRef._meta.get_field('filedata'), arg_tuple[1])
        self.assertEqual(abs_path, arg_tuple[2].path)

        self.assertEqual(basename, dl_filefield.base_name)
