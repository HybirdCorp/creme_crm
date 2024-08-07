from django.urls import reverse

from creme.creme_core.models import FakeDocument, FakeFolder, FileRef

from ..base import CremeTestCase


class DownloadViewTestCase(CremeTestCase):
    def test_download_filefield__errors(self):
        user = self.login_as_root_and_get()

        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=user,
            title='Selfie with RedTail',
            linked_folder=folder,
        )

        ct_id = doc.entity_type_id
        self.assertGET404(reverse('creme_core__download', args=(ct_id, doc.id, 'unknown')))

        # Empty file
        self.assertGET404(reverse('creme_core__download', args=(ct_id, doc.id, 'filedata')))

    def test_download_filefield__superuser_OK(self):
        user = self.login_as_root_and_get()
        file_content = 'I am the content'
        path = self.create_uploaded_file(
            file_name='DownloadViewTestCase_test_download_filefield_superOK.txt',
            dir_name='views',
            content=file_content,
        )
        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=user,
            title='Selfie with RedTail',
            linked_folder=folder,
            filedata=path,
        )

        url = reverse('creme_core__download', args=(doc.entity_type_id, doc.id, 'filedata'))
        response = self.assertGET200(url, follow=True)
        # self.assertEqual('text/plain; charset=utf-8', response['Content-Type'])  TODO ??
        self.assertEqual('text/plain', response['Content-Type'])

        cdisp = response['Content-Disposition']
        self.assertStartsWith(
            cdisp,
            'attachment; filename="DownloadViewTestCase_test_download_filefield',
        )
        self.assertEndsWith(cdisp, '.txt"')
        self.assertEqual(
            file_content.encode(),
            b''.join(response.streaming_content)
        )

        self.assertPOST405(url)

    def test_download_filefield__basename(self):
        user = self.login_as_root_and_get()
        path = self.create_uploaded_file(
            file_name='DownloadViewTestCase_test_download_filefield_basename.txt',
            dir_name='views',
        )
        temp_file = FileRef.objects.create(user=user, filedata=path, basename='test.txt')

        response = self.assertGET200(temp_file.get_download_absolute_url(), follow=True)
        # self.assertEqual('text/plain; charset=utf-8', response['Content-Type'])  TODO ?
        self.assertEqual('text/plain', response['Content-Type'])

        self.assertEqual(
            f'attachment; filename="{temp_file.basename}"',
            response['Content-Disposition'],
        )
        # Consume stream to avoid error message "ResourceWarning: unclosed file..."
        _ = [*response.streaming_content]

    def test_download_filefield__standard_user_OK(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all=['VIEW'], model=FakeDocument)

        path = self.create_uploaded_file(
            file_name='DownloadViewTestCase_test_download_filefield_standardOK.txt',
            dir_name='views',
        )
        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=self.get_root_user(),
            title='Selfie with RedTail',
            linked_folder=folder,
            filedata=path,
        )
        self.assertTrue(user.has_perm_to_view(doc))

        response = self.assertGET200(
            reverse('creme_core__download', args=(doc.entity_type_id, doc.id, 'filedata')),
            follow=True,
        )
        # Consume stream to avoid error message "ResourceWarning: unclosed file..."
        _ = [*response.streaming_content]

    def test_download_filefield__standard_user_error(self):
        user = self.login_as_standard()

        path = self.create_uploaded_file(
            file_name='DownloadViewTestCase_test_download_filefield_standarderror.txt',
            dir_name='views',
        )
        folder = FakeFolder.objects.create(user=user, title="Faye's pix")
        doc = FakeDocument.objects.create(
            user=self.get_root_user(),
            title='Selfie with RedTail',
            linked_folder=folder,
            filedata=path,
        )
        self.assertFalse(user.has_perm_to_view(doc))

        self.assertGET403(
            reverse('creme_core__download', args=(doc.entity_type_id, doc.id, 'filedata')),
            follow=True,
        )
