# -*- coding: utf-8 -*-

from os.path import join
from unittest import skipIf

from django.conf import settings
from django.urls import reverse

from creme import documents
from creme.creme_core.tests.base import CremeTestCase
from creme.documents import constants

skip_document_tests = documents.document_model_is_custom()
skip_folder_tests   = documents.folder_model_is_custom()

Document = documents.get_document_model()
Folder = documents.get_folder_model()


def skipIfCustomDocument(test_func):
    return skipIf(skip_document_tests, 'Custom document model in use')(test_func)


def skipIfCustomFolder(test_func):
    return skipIf(skip_folder_tests, 'Custom folder model in use')(test_func)


class _DocumentsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ADD_DOC_URL = reverse('documents__create_document')

    def _create_doc(self, title,
                    file_obj=None, folder=None, description=None, user=None,
                    **extra_data):
        file_obj = file_obj or self.build_filedata(f'{title} : Content')
        folder = folder or Folder.objects.all()[0]
        user = user or self.user
        data = {
            'user': user.pk,
            'title': title,
            'filedata': file_obj,
            'linked_folder': folder.id,
            **extra_data
        }

        if description is not None:
            data['description'] = description

        response = self.client.post(self.ADD_DOC_URL, follow=True, data=data)
        self.assertNoFormError(response)

        return self.get_object_or_fail(Document, title=title)

    def _create_image(self, ident=1, user=None, title=None, folder=None, description=None):
        IMAGE_PATHS = {
            1: 'creme_22.png',
            2: 'add_16.png',
            3: 'edit_16.png',
            4: 'delete_16.png',
            5: 'memo_16.png',
            6: 'info_16.png',
            7: 'refresh_16.png',
        }

        name = IMAGE_PATHS[ident]

        with open(
            join(settings.CREME_ROOT, 'static', 'chantilly', 'images', name), 'rb',
        ) as image_file:
            return self._create_doc(
                title=title or name,
                file_obj=image_file,
                folder=folder or Folder.objects.get(uuid=constants.UUID_FOLDER_IMAGES),
                description=description,
                user=user,
            )
