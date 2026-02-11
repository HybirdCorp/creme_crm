from decimal import Decimal

from django.utils.translation import gettext as _

from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
from creme.products.models import Category, SubCategory

from ..base import (
    Document,
    Product,
    Service,
    _ProductsTestCase,
    skipIfCustomProduct,
)


@skipIfCustomProduct
class MassImportTestCase(MassImportBaseTestCaseMixin, _ProductsTestCase):
    def test_product__default_categories(self):
        "Categories not in CSV."
        user = self.login_as_root_and_get()

        count = Product.objects.count()

        names = 'Product 01', 'Product 02'
        descriptions = 'Description #1', 'Description #2'
        prices = '10', '20.50'
        codes = 123, 456

        lines = [
            (names[0], descriptions[0], prices[0], codes[0]),
            (names[1], descriptions[1], prices[1], codes[1]),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Product)
        self.assertGET200(url)

        sub_cat = SubCategory.objects.first()

        data = {
            'step': 1,
            'document': doc.id,
            # has_header
            'user': user.id,

            'name_colselect': 1,
            'description_colselect': 2,
            'unit_price_colselect': 3,
            'code_colselect': 4,

            'categories_cat_colselect': 0,
            'categories_subcat_colselect': 0,
            # 'categories_defval': ...,

            'unit_colselect': 0,
            'quantity_per_unit_colselect': 0,
            'weight_colselect': 0,
            'stock_colselect': 0,
            'web_site_colselect': 0,

            # 'property_types',
            # 'fixed_relations',
            # 'dyn_relations',
        }

        # Validation errors ------------------------
        msg = _('Select a valid sub-category.')
        response1 = self.assertPOST200(url, follow=True, data=data)
        self.assertFormError(response1.context['form'], field='categories', errors=msg)

        # ---
        response2 = self.assertPOST200(
            url, follow=True, data={**data, 'categories_subcat_defval': self.UNUSED_PK},
        )
        self.assertFormError(response2.context['form'], field='categories', errors=msg)

        # ---
        response3 = self.assertPOST200(
            url, follow=True, data={**data, 'categories_subcat_defval': 'not a int'},
        )
        self.assertFormError(response3.context['form'], field='categories', errors=msg)

        # OK ------------------------
        response4 = self.client.post(
            url, follow=True, data={**data, 'categories_subcat_defval': sub_cat.id},
        )
        self.assertNoFormError(response4)

        job = self._execute_job(response4)
        self.assertEqual(count + len(lines), Product.objects.count())

        for i, l in enumerate(lines):
            product = self.get_object_or_fail(Product, name=names[i])
            self.assertEqual(user,               product.user)
            self.assertEqual(descriptions[i],    product.description)
            self.assertEqual(Decimal(prices[i]), product.unit_price)
            self.assertEqual(codes[i],           product.code)

            self.assertIsNone(product.stock)

            self.assertEqual(sub_cat,          product.sub_category)
            self.assertEqual(sub_cat.category, product.category)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))
        self._assertNoResultError(results)

    def test_product__import_categories__no_creation(self):
        "Categories in CSV; no creation."
        user = self.login_as_root_and_get()
        count = Product.objects.count()

        cat1 = Category.objects.create(name='(Test) Video games')
        sub_cat11 = SubCategory.objects.create(name='Puzzle', category=cat1)
        sub_cat12 = SubCategory.objects.create(name='Action', category=cat1)

        cat2 = Category.objects.create(name='(Test) DVD')
        sub_cat21 = SubCategory.objects.create(name='Thriller', category=cat2)
        # NB: same name than sub_cat12
        sub_cat22 = SubCategory.objects.create(name='Action',   category=cat2)

        names = ['Product %2i' % i for i in range(1, 7)]

        lines = [
            (names[0], '',        ''),
            (names[1], cat2.name, sub_cat21.name),
            # No problem with the duplicated name of SubCategory
            (names[2], cat2.name, sub_cat22.name),
            # KO: default sub-category is not corresponding
            (names[3], cat2.name, ''),
            # KO: even if the SubCategory corresponds to the default Category
            (names[4], 'invalid', sub_cat12.name),
            # KO
            (names[5], cat1.name, 'invalid'),
        ]

        url = self._build_import_url(Product)
        doc = self._build_csv_doc(lines, user=user)
        description = 'Imported from CSV'
        price = '12'
        code = 489
        data = {
            'step': 1,
            'document': doc.id,
            # has_header
            'user': user.id,

            'name_colselect': 1,

            'description_colselect': 0,
            'description_defval': description,

            'unit_price_colselect': 0,
            'unit_price_defval': price,

            'code_colselect': 0,
            'code_defval': code,

            'categories_cat_colselect': 2,
            'categories_subcat_colselect': 3,
            'categories_subcat_defval': sub_cat11.pk,

            'unit_colselect': 0,
            'quantity_per_unit_colselect': 0,
            'weight_colselect': 0,
            'stock_colselect': 0,
            'web_site_colselect': 0,

            # 'property_types',
            # 'fixed_relations',
            # 'dyn_relations',
        }

        # Validation error ------------------------
        response1 = self.assertPOST200(
            url, follow=True, data={**data, 'categories_subcat_colselect': 0},
        )
        self.assertFormError(
            response1.context['form'],
            field='categories',
            errors=_(
                'Select a column for the sub-category if you select a column for the category.'
            ),
        )

        # OK --------------------------------------
        response2 = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response2)

        job = self._execute_job(response2)
        self.assertEqual(count + 3, Product.objects.count())

        def get_product(i):
            product = self.get_object_or_fail(Product, name=names[i])
            self.assertEqual(description,    product.description)
            self.assertEqual(Decimal(price), product.unit_price)
            self.assertEqual(code,           product.code)

            self.assertIsNone(product.stock)

            return product

        product1 = get_product(0)
        self.assertEqual(cat1,      product1.category)
        self.assertEqual(sub_cat11, product1.sub_category)

        product2 = get_product(1)
        self.assertEqual(cat2,      product2.category)
        self.assertEqual(sub_cat21, product2.sub_category)

        product3 = get_product(2)
        self.assertEqual(cat2,      product3.category)
        self.assertEqual(sub_cat22, product3.sub_category)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(3, len(jr_errors))

        jr_error1 = jr_errors[0]
        self.assertListEqual(
            [
                _(
                    'The category «{cat}» and the sub-category «{sub_cat}» are not matching.'
                ).format(
                    cat=cat2,
                    sub_cat=sub_cat11,
                ),
                # TODO: the message should indicate the name of the field.
                _('This field cannot be null.'),
                _('This field cannot be null.'),
            ],
            jr_error1.messages
        )
        self.assertIsNone(jr_error1.entity)

        self.assertListEqual(
            [
                _('The category «{}» does not exist').format('invalid'),
                _('This field cannot be null.'),
                _('This field cannot be null.'),
            ],
            jr_errors[1].messages
        )

        self.assertListEqual(
            [
                _('The sub-category «{}» does not exist').format('invalid'),
                _('This field cannot be null.'),
                _('This field cannot be null.'),
            ],
            jr_errors[2].messages
        )

    def test_product__import_categories__creation(self):
        "Categories in CSV; creation of Category/SubCategory."
        user = self.login_as_root_and_get()
        count = Product.objects.count()

        cat1 = Category.objects.create(name='(Test) Video games')
        sub_cat11 = SubCategory.objects.create(name='Puzzle', category=cat1)

        cat2 = Category.objects.create(name='(Test) DVD')
        sub_cat21 = SubCategory.objects.create(name='Thriller', category=cat2)
        sub_cat22_name = 'Action'

        cat3_name = 'Books'
        sub_cat31_name = 'Sci-Fi'

        names = [f'Product {i}' for i in range(1, 5)]

        lines = [
            (names[0], '', ''),
            (names[1], cat2.name, sub_cat21.name),
            (names[2], cat2.name, sub_cat22_name),
            (names[3], cat3_name, sub_cat31_name),
        ]
        doc = self._build_csv_doc(lines, user=user)

        description = 'Imported from CSV'
        price = '12'
        code = 489
        response = self.client.post(
            self._build_import_url(Product), follow=True,
            data={
                'step': 1,
                'document': doc.id,
                # has_header
                'user': user.id,

                'name_colselect': 1,

                'description_colselect': 0,
                'description_defval': description,

                'unit_price_colselect': 0,
                'unit_price_defval': price,

                'code_colselect': 0,
                'code_defval': code,

                'categories_cat_colselect': 2,
                'categories_subcat_colselect': 3,
                'categories_subcat_defval': sub_cat11.pk,
                'categories_create': 'on',  # <==

                'unit_colselect': 0,
                'quantity_per_unit_colselect': 0,
                'weight_colselect': 0,
                'stock_colselect': 0,
                'web_site_colselect': 0,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + len(lines), Product.objects.count())

        def get_product(i):
            product = self.get_object_or_fail(Product, name=names[i])
            self.assertEqual(description, product.description)
            self.assertEqual(Decimal(price), product.unit_price)
            self.assertEqual(code, product.code)

            self.assertIsNone(product.stock)

            return product

        product1 = get_product(0)
        self.assertEqual(cat1,      product1.category)
        self.assertEqual(sub_cat11, product1.sub_category)

        product2 = get_product(1)
        self.assertEqual(cat2,      product2.category)
        self.assertEqual(sub_cat21, product2.sub_category)

        product3 = get_product(2)
        self.assertEqual(cat2,           product3.category)
        self.assertEqual(sub_cat22_name, product3.sub_category.name)

        product4 = get_product(3)
        self.assertEqual(cat3_name,      product4.category.name)
        self.assertEqual(sub_cat31_name, product4.sub_category.name)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))
        self._assertNoResultError(results)

    def test_product__import_categories__creation_forbidden(self):
        "Categories in CSV; want to create Category but not it is allowed."
        user = self.login_as_standard(
            allowed_apps=['products', 'documents'],
            creatable_models=[Product, Document],
        )
        self.add_credentials(user.role, own='*')

        count = Product.objects.count()

        cat1 = Category.objects.create(name='(Test) Video games')
        sub_cat11 = SubCategory.objects.create(name='Puzzle', category=cat1)

        cat2 = Category.objects.create(name='(Test) DVD')
        sub_cat21 = SubCategory.objects.create(name='Thriller', category=cat2)

        names = ['Product %2i' % i for i in range(1, 5)]
        lines = [
            (names[0], '', ''),
            (names[1], cat2.name, sub_cat21.name),
            (names[2], cat2.name, 'Action'),
            (names[3], 'Books',   'Sci-Fi'),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Product)
        self.assertGET200(url)

        data = {
            'step': 1,
            'document': doc.id,
            # has_header
            'user': user.id,

            'name_colselect': 1,

            'description_colselect': 0,
            'description_defval': 'Imported from CSV',

            'unit_price_colselect': 0,
            'unit_price_defval': '12',

            'code_colselect': 0,
            'code_defval': 489,

            'categories_cat_colselect': 2,
            'categories_subcat_colselect': 3,
            'categories_subcat_defval': sub_cat11.pk,

            'unit_colselect': 0,
            'quantity_per_unit_colselect': 0,
            'weight_colselect': 0,
            'stock_colselect': 0,
            'web_site_colselect': 0,

            # 'property_types',
            # 'fixed_relations',
            # 'dyn_relations',
        }

        # Validation error -----------
        response1 = self.assertPOST200(
            url, follow=True, data={**data, 'categories_create': 'on'},
        )
        self.assertFormError(
            response1.context['form'],
            field='categories', errors='You cannot create Category or SubCategory',
        )

        # OK --------------------------
        response2 = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response2)

        self._execute_job(response2)
        self.assertEqual(count + 2, Product.objects.count())

    def test_service(self):
        "Categories in CSV; creation of Category/SubCategory."
        user = self.login_as_root_and_get()
        count = Service.objects.count()

        cat1 = Category.objects.create(name='(Test) Shipping')
        sub_cat11 = SubCategory.objects.create(name='Air shipping', category=cat1)

        cat2 = Category.objects.create(name='(Test) Cooking')
        sub_cat21 = SubCategory.objects.create(name='Cakes', category=cat2)
        sub_cat22_name = 'Vegetables'

        cat3_name = 'Books'
        sub_cat31_name = 'Sci-Fi'

        names = [f'Service {i}' for i in range(1, 5)]
        lines = [
            (names[0], '', ''),
            (names[1], cat2.name, sub_cat21.name),
            (names[2], cat2.name, sub_cat22_name),
            (names[3], cat3_name, sub_cat31_name),
        ]
        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(Service)
        self.assertGET200(url)

        # ---
        description = 'Service imported from CSV'
        price = '39'
        reference = '489'
        response = self.client.post(
            url,
            follow=True,
            data={
                'step': 1,
                'document': doc.id,
                # has_header
                'user': user.id,

                'name_colselect': 1,

                'description_colselect': 0,
                'description_defval': description,

                'unit_price_colselect': 0,
                'unit_price_defval': price,

                'reference_colselect': 0,
                'reference_defval': reference,

                'categories_cat_colselect': 2,
                'categories_subcat_colselect': 3,
                'categories_subcat_defval': sub_cat11.pk,
                'categories_create': 'on',  # <==

                'unit_colselect': 0,
                'quantity_per_unit_colselect': 0,
                'countable_colselect': 0,
                'web_site_colselect': 0,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + len(lines), Service.objects.count())

        def get_service(i):
            service = self.get_object_or_fail(Service, name=names[i])
            self.assertEqual(description, service.description)
            self.assertEqual(Decimal(price), service.unit_price)
            self.assertEqual(reference, service.reference)

            self.assertFalse(service.countable)
            self.assertFalse(service.web_site)

            return service

        service1 = get_service(0)
        self.assertEqual(cat1,      service1.category)
        self.assertEqual(sub_cat11, service1.sub_category)

        service2 = get_service(1)
        self.assertEqual(cat2,      service2.category)
        self.assertEqual(sub_cat21, service2.sub_category)

        service3 = get_service(2)
        self.assertEqual(cat2,           service3.category)
        self.assertEqual(sub_cat22_name, service3.sub_category.name)

        service4 = get_service(3)
        self.assertEqual(cat3_name,      service4.category.name)
        self.assertEqual(sub_cat31_name, service4.sub_category.name)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))
        self._assertNoResultError(results)
