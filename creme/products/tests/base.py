from unittest import skipIf

from creme import documents, products
from creme.creme_core.tests.base import CremeTestCase
from creme.documents.tests.base import DocumentsTestCaseMixin

skip_product_tests = products.product_model_is_custom()
skip_service_tests = products.service_model_is_custom()

Document = documents.get_document_model()
Folder   = documents.get_folder_model()

Product = products.get_product_model()
Service = products.get_service_model()


def skipIfCustomProduct(test_func):
    return skipIf(skip_product_tests, 'Custom Product model in use')(test_func)


def skipIfCustomService(test_func):
    return skipIf(skip_service_tests, 'Custom Service model in use')(test_func)


class _ProductsTestCase(DocumentsTestCaseMixin, CremeTestCase):
    EXTRA_CATEGORY_KEY = 'cform_extra-products_subcategory'

    def login_as_basic_user(self, creatable_model):
        user = self.login_as_standard(
            allowed_apps=['products', 'documents'],
            creatable_models=[creatable_model, Document],
        )
        self.add_credentials(user.role, all='!LINK', own='*')

        return user
