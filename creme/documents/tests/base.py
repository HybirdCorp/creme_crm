# -*- coding: utf-8 -*-

from os.path import basename, join
from tempfile import NamedTemporaryFile
from unittest import skipIf

from django.conf import settings
from django.core.urlresolvers import reverse
# from django.utils.translation import ugettext as _

from creme.creme_core.tests.base import CremeTestCase

try:
    from creme import documents
    from creme.documents import constants

    skip_document_tests = documents.document_model_is_custom()
    skip_folder_tests   = documents.folder_model_is_custom()

    Document = documents.get_document_model()
    Folder = documents.get_folder_model()
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

    skip_document_tests = skip_folder_tests = False


def skipIfCustomDocument(test_func):
    return skipIf(skip_document_tests, 'Custom document model in use')(test_func)


def skipIfCustomFolder(test_func):
    return skipIf(skip_folder_tests, 'Custom folder model in use')(test_func)


class _DocumentsTestCase(CremeTestCase):
    clean_files_in_teardown = True  # see CremeTestCase

    @classmethod
    def setUpClass(cls):
        # CremeTestCase.setUpClass()
        super(_DocumentsTestCase, cls).setUpClass()
        # cls.populate('creme_core', 'documents')
        cls.ADD_DOC_URL = reverse('documents__create_document')

    def _build_filedata(self, content_str, suffix='.txt'):
        tmpfile = NamedTemporaryFile(suffix=suffix, delete=False)
        tmpfile.write(content_str)
        tmpfile.flush()

        # We close and reopen in order to have a file with the right name (so we must specify delete=False)
        tmpfile.close()

        name = tmpfile.name

        return open(name, 'rb'), basename(name)

    def _create_doc(self, title, file_obj=None, folder=None, description=None, user=None):
        file_obj = file_obj or self._build_filedata('%s : Content' % title)[0]
        folder = folder or Folder.objects.all()[0]
        user = user or self.user
        data = {'user':     user.pk,
                'title':    title,
                'filedata': file_obj,
                'folder':   folder.id,
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
        image_file = open(join(settings.CREME_ROOT, 'static', 'chantilly', 'images', name), 'rb')

        return self._create_doc(title=title or name,
                                file_obj=image_file,
                                # folder=folder or Folder.objects.get(title=_('Images')),
                                folder=folder or Folder.objects.get(uuid=constants.UUID_FOLDER_IMAGES),
                                description=description,
                                user=user,
                               )
