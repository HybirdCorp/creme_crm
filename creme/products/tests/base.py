# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump
from unittest import skipIf

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import SetCredentials
from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
from creme.documents import get_document_model
from creme.documents.tests.base import _DocumentsTestCase

from .. import product_model_is_custom, service_model_is_custom

skip_product_tests = product_model_is_custom()
skip_service_tests = service_model_is_custom()


def skipIfCustomProduct(test_func):
    return skipIf(skip_product_tests, 'Custom Product model in use')(test_func)


def skipIfCustomService(test_func):
    return skipIf(skip_service_tests, 'Custom Service model in use')(test_func)


class _ProductsTestCase(_DocumentsTestCase, MassImportBaseTestCaseMixin):
    EXTRA_CATEGORY_KEY = 'cform_extra-products_subcategory'

    def _cat_field(self, category, sub_category):
        return json_dump({'category': category.id, 'subcategory': sub_category.id})

    def login_as_basic_user(self, creatable_model):
        user = self.login(
            is_superuser=False, allowed_apps=['products', 'documents'],
            creatable_models=[creatable_model, get_document_model()],
        )

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
                # | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        return user
