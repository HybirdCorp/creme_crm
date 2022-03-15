# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FakeContact, SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.documents import get_document_model, get_folder_model

from .. import get_product_model
from ..bricks import ImagesBrick
from ..models import Category, SubCategory
from .base import _ProductsTestCase, skipIfCustomProduct

Product = get_product_model()


@skipIfCustomProduct
class ProductTestCase(BrickTestCaseMixin, _ProductsTestCase):
    def test_populate(self):
        self.assertTrue(Category.objects.exists())
        self.assertTrue(SubCategory.objects.exists())

    def test_subcategories_view(self):
        self.login()

        self.assertGET404(reverse('products__subcategories', args=(0,)))

        name1 = 'subcat1'
        name2 = 'subcat2'
        cat = Category.objects.create(name='category', description='description')

        create_subcat = partial(SubCategory.objects.create, category=cat)
        subcat1 = create_subcat(name=name1, description='description')
        subcat2 = create_subcat(name=name2, description='description')

        response = self.assertGET200(reverse('products__subcategories', args=(cat.id,)))
        self.assertListEqual(
            [[subcat1.id, name1], [subcat2.id, name2]],
            response.json(),
        )

    @skipIfCustomProduct
    def test_detailview01(self):
        "No image."
        user = self.login()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        response = self.assertGET200(product.get_absolute_url())
        self.assertTemplateUsed(response, 'products/view_product.html')
        self.assertTemplateUsed(response, 'products/bricks/images.html')

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            ImagesBrick.id_,
        )
        self.assertEqual(_('Images'), self.get_brick_title(brick_node))

        buttons_node = self.get_brick_header_buttons(brick_node)
        self.assertBrickHeaderHasButton(
            buttons_node=buttons_node,
            url=reverse('products__add_images_to_product', args=(product.id,)),
            label=_('Add images'),
        )

        msg_node = self.get_html_node_or_fail(brick_node, './/div[@class="brick-tiles-empty"]')
        self.assertEqual(_('No image for the moment'), msg_node.text)

    @skipIfCustomProduct
    def test_detailview02(self):
        "With image."
        user = self.login()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        create_image = partial(
            self._create_image, user=user,
            folder=get_folder_model().objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)

        product.images.set([img_1, img_2])

        ImagesBrick.page_size = max(4, settings.BLOCK_SIZE)

        response = self.assertGET200(product.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            ImagesBrick.id_,
        )
        self.assertEqual(
            _('{count} Images').format(count=2),
            self.get_brick_title(brick_node),
        )
        self.get_html_node_or_fail(
            brick_node, f".//a[@href='{img_1.get_absolute_url()}']"
        )
        self.get_html_node_or_fail(
            brick_node, f".//a[@href='{img_2.get_absolute_url()}']"
        )

    @skipIfCustomProduct
    def test_createview01(self):
        user = self.login()

        self.assertEqual(0, Product.objects.count())

        url = reverse('products__create_product')
        self.assertGET200(url)

        name = 'Eva00'
        code = 42
        sub_cat = SubCategory.objects.all()[0]
        cat = sub_cat.category
        description = 'A fake god'
        unit_price = '1.23'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'code':         code,
                'description':  description,
                'unit_price':   unit_price,
                'unit':         'anything',

                self.EXTRA_CATEGORY_KEY: self._cat_field(cat, sub_cat),
            },
        )
        self.assertNoFormError(response)

        products = Product.objects.all()
        self.assertEqual(1, len(products))

        product = products[0]
        self.assertEqual(name,                product.name)
        self.assertEqual(code,                product.code)
        self.assertEqual(description,         product.description)
        self.assertEqual(Decimal(unit_price), product.unit_price)
        self.assertEqual(cat,                 product.category)
        self.assertEqual(sub_cat,             product.sub_category)

        self.assertRedirects(response, product.get_absolute_url())

    @skipIfCustomProduct
    def test_createview02(self):
        "Images + credentials."
        user = self.login_as_basic_user(Product)

        create_image = partial(
            self._create_image, user=user,
            folder=get_folder_model().objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)
        img_3 = create_image(ident=3, user=self.other_user)

        self.assertTrue(user.has_perm_to_link(img_1))
        self.assertFalse(user.has_perm_to_link(img_3))

        name = 'Eva00'
        sub_cat = SubCategory.objects.all()[0]

        def post(*images):
            return self.client.post(
                reverse('products__create_product'), follow=True,
                data={
                    'user':        user.pk,
                    'name':        name,
                    'code':        42,
                    'description': 'A fake god',
                    'unit_price':  '1.23',
                    'unit':        'anything',
                    'images':      self.formfield_value_multi_creator_entity(*images),

                    self.EXTRA_CATEGORY_KEY: self._cat_field(
                        sub_cat.category, sub_cat,
                    ),
                },
            )

        response1 = post(img_1, img_3)
        self.assertEqual(200, response1.status_code)
        self.assertFormError(
            response1, 'form', 'images',
            _('Some entities are not linkable: {}').format(img_3),
        )

        response2 = post(img_1, img_2)
        self.assertNoFormError(response2)

        product = self.get_object_or_fail(Product, name=name)
        self.assertSetEqual({img_1, img_2}, {*product.images.all()})

    @skipIfCustomProduct
    def test_editview(self):
        user = self.login()

        name = 'Eva00'
        code = 42
        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name=name, description='A fake god',
            unit_price=Decimal('1.23'), code=code,
            category=sub_cat.category, sub_category=sub_cat,
        )
        url = product.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            subcat_f = fields[self.EXTRA_CATEGORY_KEY]

        self.assertNotIn('images', fields)
        self.assertEqual(sub_cat, subcat_f.initial)
        self.assertEqual(user, subcat_f.user)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'code':         product.code,
                'description':  product.description,
                'unit_price':   unit_price,
                'unit':         'anything',

                self.EXTRA_CATEGORY_KEY: self._cat_field(
                    product.category, product.sub_category,
                ),
            },
        )
        self.assertNoFormError(response)

        product = self.refresh(product)
        self.assertEqual(name,                product.name)
        self.assertEqual(Decimal(unit_price), product.unit_price)

    @skipIfCustomProduct
    def test_listview(self):
        user = self.login()

        cat = Category.objects.all()[0]
        create_prod = partial(
            Product.objects.create,
            user=user,
            description='A fake god', unit_price=Decimal('1.23'),
            category=cat, sub_category=SubCategory.objects.all()[0],
        )
        products = [
            create_prod(name='Eva00', code=42),
            create_prod(name='Eva01', code=43),
        ]

        response = self.assertGET200(Product.get_lv_absolute_url())

        with self.assertNoException():
            products_page = response.context['page_obj']

        self.assertEqual(2, products_page.paginator.count)
        self.assertSetEqual({*products}, {*products_page.object_list})

    def test_delete_category01(self):
        self.login()

        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(
            name='Eva', description='Fake gods', category=cat,
        )

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('products', 'subcategory', sub_cat.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(SubCategory).job
        job.type.execute(job)
        self.assertDoesNotExist(sub_cat)

    def _build_product_cat_subcat(self):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(
            name='Eva', description='Fake gods', category=cat,
        )
        product = Product.objects.create(
            user=self.user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=cat, sub_category=sub_cat,
        )

        return product, cat, sub_cat

    @skipIfCustomProduct
    def test_delete_category02(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('products', 'subcategory', sub_cat.id)
        ))
        self.assertFormError(
            response, 'form',
            'replace_products__product_sub_category',
            _('Deletion is not possible.')
        )

    def test_delete_category03(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('products', 'category', cat.id),
        ))
        self.assertFormError(
            response, 'form', 'replace_products__product_category',
            _('Deletion is not possible.'),
        )

    def test_edit_inner_category(self):
        user = self.login()

        sub_cat = SubCategory.objects.order_by('category')[0]
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        url = self.build_inneredit_url(product, 'category')
        self.assertGET200(url)

        next_sub_cat = SubCategory.objects.order_by('category')[1]
        response = self.client.post(
            url,
            data={
                'sub_category': self._cat_field(
                    category=next_sub_cat.category,
                    sub_category=next_sub_cat,
                ),
            },
        )
        self.assertNoFormError(response)

        product = self.refresh(product)
        self.assertEqual(next_sub_cat, product.sub_category)
        self.assertEqual(next_sub_cat.category, product.category)

    def test_edit_inner_category_invalid(self):
        user = self.login()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        url = self.build_inneredit_url(product, 'category')
        self.assertGET200(url)

        next_sub_cat = SubCategory.objects.exclude(category=sub_cat.category)[0]
        response = self.client.post(
            url,
            data={
                'sub_category': self._cat_field(
                    category=sub_cat.category,
                    sub_category=next_sub_cat,
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'sub_category',
            _('This sub-category causes constraint error.'),
        )

        product = self.refresh(product)
        self.assertEqual(sub_cat, product.sub_category)
        self.assertEqual(sub_cat.category, product.category)

    def test_edit_bulk_category(self):
        user = self.login()

        sub_cat = SubCategory.objects.order_by('category')[0]
        create_product = partial(
            Product.objects.create,
            user=user, description='A fake god', unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )

        product = create_product(name='Eva00', code=42)
        product2 = create_product(name='Eva01', code=43)

        url = self.build_bulkupdate_url(Product, 'category')
        self.assertGET200(url)

        next_sub_cat = SubCategory.objects.order_by('category')[1]
        response = self.client.post(
            url,
            data={
                '_bulk_fieldname': url,
                'sub_category': self._cat_field(
                    category=sub_cat.category,
                    sub_category=next_sub_cat,
                ),
                'entities': [product.pk, product2.pk],
            },
        )
        self.assertNoFormError(response)

        product = self.refresh(product)
        self.assertEqual(next_sub_cat, product.sub_category)
        self.assertEqual(next_sub_cat.category, product.category)

        product2 = self.refresh(product2)
        self.assertEqual(next_sub_cat, product2.sub_category)
        self.assertEqual(next_sub_cat.category, product2.category)

    def test_edit_bulk_category_invalid(self):
        user = self.login()

        sub_cat = SubCategory.objects.all()[0]
        create_product = partial(
            Product.objects.create,
            user=user, description='A fake god', unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )

        product = create_product(name='Eva00', code=42)
        product2 = create_product(name='Eva01', code=43)

        url = self.build_bulkupdate_url(Product, 'category')
        self.assertGET200(url)

        next_sub_cat = SubCategory.objects.exclude(category=sub_cat.category)[0]
        response = self.client.post(
            url,
            data={
                '_bulk_fieldname': url,
                'sub_category': self._cat_field(
                    category=sub_cat.category,
                    sub_category=next_sub_cat,
                ),
                'entities': [product.id, product2.id],
            },
        )
        self.assertFormError(
            response, 'form', 'sub_category',
            _('This sub-category causes constraint error.'),
        )

        product = self.refresh(product)
        self.assertEqual(sub_cat, product.sub_category)
        self.assertEqual(sub_cat.category, product.category)

        product2 = self.refresh(product2)
        self.assertEqual(sub_cat, product2.sub_category)
        self.assertEqual(sub_cat.category, product2.category)

    def test_update_bulk_category(self):
        user = self.login()

        sub_cat = SubCategory.objects.order_by('category')[0]
        create_product = partial(
            Product.objects.create,
            user=user, description='A fake god', unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )

        product1 = create_product(name='Eva00', code=42)
        product2 = create_product(name='Eva01', code=43)

        url = self.build_bulkupdate_url(Product, 'category')
        self.assertGET200(url)

        next_sub_cat = SubCategory.objects.order_by('category')[1]
        response = self.client.post(
            url,
            data={
                '_bulk_fieldname': url,
                'sub_category': self._cat_field(
                    category=next_sub_cat.category,
                    sub_category=next_sub_cat,
                ),
                'entities': [product1.pk, product2.pk],
            },
        )
        self.assertNoFormError(response)

        product1 = self.refresh(product1)
        self.assertEqual(next_sub_cat,          product1.sub_category)
        self.assertEqual(next_sub_cat.category, product1.category)

        product2 = self.refresh(product2)
        self.assertEqual(next_sub_cat,          product2.sub_category)
        self.assertEqual(next_sub_cat.category, product2.category)

    def test_update_bulk_category_invalid(self):
        user = self.login()

        sub_cat = SubCategory.objects.all()[0]
        create_product = partial(
            Product.objects.create,
            user=user, description='A fake god', unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )

        product1 = create_product(name='Eva00', code=42)
        product2 = create_product(name='Eva01', code=43)

        url = self.build_bulkupdate_url(Product, 'category')
        self.assertGET200(url)

        next_sub_cat = SubCategory.objects.exclude(category=sub_cat.category)[0]
        response = self.client.post(
            url,
            data={
                '_bulk_fieldname': url,
                'sub_category': self._cat_field(
                    category=sub_cat.category,
                    sub_category=next_sub_cat,
                ),
                'entities': [product1.pk, product2.pk],
            },
        )
        self.assertFormError(
            response, 'form', 'sub_category',
            _('This sub-category causes constraint error.'),
        )

        product1 = self.refresh(product1)
        self.assertEqual(sub_cat,          product1.sub_category)
        self.assertEqual(sub_cat.category, product1.category)

        product2 = self.refresh(product2)
        self.assertEqual(sub_cat, product2.sub_category)
        self.assertEqual(sub_cat.category, product2.category)

    def test_add_images01(self):
        user = self.login_as_basic_user(Product)

        create_image = partial(
            self._create_image, user=user,
            folder=get_folder_model().objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)
        img_3 = create_image(ident=3)
        img_4 = create_image(ident=4, user=self.other_user)
        self.assertTrue(user.has_perm_to_link(img_1))
        self.assertFalse(user.has_perm_to_link(img_4))

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )
        product.images.set([img_3])

        url = reverse('products__add_images_to_product', args=(product.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        context = response1.context
        self.assertEqual(
            _('New images for «{entity}»').format(entity=product),
            context.get('title'),
        )
        self.assertEqual(_('Link the images'), context.get('submit_label'))

        def post(*images):
            return self.client.post(
                url, follow=True,
                data={'images': self.formfield_value_multi_creator_entity(*images)},
            )

        response2 = post(img_1, img_4)
        self.assertEqual(200, response2.status_code)
        self.assertFormError(
            response2, 'form', 'images',
            _('Some entities are not linkable: {}').format(img_4),
        )

        response3 = post(img_1, img_2)
        self.assertNoFormError(response3)
        self.assertSetEqual({img_1, img_2, img_3}, {*product.images.all()})

        # ------------
        img_5 = create_image(ident=5, user=user)
        response4 = post(img_1, img_5)
        self.assertEqual(200, response4.status_code)
        # self.assertFormError(response4, 'form', 'images', _('This entity does not exist.'))
        self.assertFormError(
            response4, 'form', 'images',
            _('«%(entity)s» violates the constraints.') % {'entity': img_1},
        )

    def test_add_images02(self):
        "Related is not a Product."
        user = self.login()
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        self.assertGET404(reverse('products__add_images_to_product', args=(rei.id,)))

    def test_remove_image(self):
        user = self.login(
            is_superuser=False,
            allowed_apps=['documents', 'products'],
            creatable_models=[get_document_model()],
        )
        creds = SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_ALL,
        )

        create_image = self._create_image
        img_1 = create_image(ident=1, user=user)
        img_2 = create_image(ident=2, user=user)

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )
        product.images.set([img_1, img_2])

        url = reverse('products__remove_image', args=(product.id,))
        data = {'id': img_1.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertListEqual([img_2], [*product.images.all()])

        # Not a Product/Service ---
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        self.assertPOST404(
            reverse('products__remove_image', args=(rei.id,)),
            data={'id': img_2.id},
        )

        # No CHANGE permission
        creds.value = EntityCredentials.VIEW | EntityCredentials.LINK
        creds.save()
        self.assertPOST403(url, data={'id': img_2.id})

    def test_mass_import01(self):
        "Categories not in CSV."
        user = self.login()

        count = Product.objects.count()

        names = 'Product 01', 'Product 02'
        descriptions = 'Description #1', 'Description #2'
        prices = '10', '20.50'
        codes = 123, 456

        lines = [
            (names[0], descriptions[0], prices[0], codes[0]),
            (names[1], descriptions[1], prices[1], codes[1]),
        ]

        doc = self._build_csv_doc(lines)
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
        self.assertFormError(response1, 'form', 'categories', msg)

        response2 = self.assertPOST200(
            url, follow=True, data={**data, 'categories_subcat_defval': self.UNUSED_PK},
        )
        self.assertFormError(response2, 'form', 'categories', msg)

        response3 = self.assertPOST200(
            url, follow=True, data={**data, 'categories_subcat_defval': 'not a int'},
        )
        self.assertFormError(response3, 'form', 'categories', msg)

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

    def test_mass_import02(self):
        "Categories in CSV ; no creation"
        user = self.login()
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
        doc = self._build_csv_doc(lines)
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
            response1, 'form', 'categories',
            _('Select a column for the sub-category if you select a column for the category.')
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

    def test_mass_import03(self):
        "Categories in CSV ; creation of Category/SubCategory"
        user = self.login()
        count = Product.objects.count()

        cat1 = Category.objects.create(name='(Test) Video games')
        sub_cat11 = SubCategory.objects.create(name='Puzzle', category=cat1)

        cat2 = Category.objects.create(name='(Test) DVD')
        sub_cat21 = SubCategory.objects.create(name='Thriller', category=cat2)
        sub_cat22_name = 'Action'

        cat3_name = 'Books'
        sub_cat31_name = 'Sci-Fi'

        names = ['Product %2i' % i for i in range(1, 5)]

        lines = [
            (names[0], '', ''),
            (names[1], cat2.name, sub_cat21.name),
            (names[2], cat2.name, sub_cat22_name),
            (names[3], cat3_name, sub_cat31_name),
        ]

        doc = self._build_csv_doc(lines)

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

    def test_mass_import04(self):
        "Categories in CSV ; want to create Category but not it is allowed."
        user = self.login(
            is_superuser=False,
            allowed_apps=['products', 'documents'],
            creatable_models=[Product, get_document_model()],
        )
        count = Product.objects.count()

        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

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

        doc = self._build_csv_doc(lines)
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
            response1, 'form', 'categories', 'You cannot create Category or SubCategory',
        )

        # OK --------------------------
        response2 = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response2)

        self._execute_job(response2)
        self.assertEqual(count + 2, Product.objects.count())
