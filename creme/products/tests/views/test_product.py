from decimal import Decimal
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core import workflows
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.core.workflow import WorkflowConditions
from creme.creme_core.models import (
    CremePropertyType,
    FakeContact,
    SetCredentials,
    Workflow,
)
from creme.products.models import Category, SubCategory

from ..base import (
    Document,
    Folder,
    Product,
    _ProductsTestCase,
    skipIfCustomProduct,
)


@skipIfCustomProduct
class ProductViewsTestCase(_ProductsTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        response = self.assertGET200(product.get_absolute_url())
        self.assertTemplateUsed(response, 'products/view_product.html')
        self.assertTemplateUsed(response, 'products/bricks/images.html')

    def test_creation(self):
        user = self.login_as_root_and_get()

        self.assertEqual(0, Product.objects.count())

        url = reverse('products__create_product')
        self.assertGET200(url)

        # ----
        name = 'Eva00'
        code = 42
        sub_cat = SubCategory.objects.all()[0]
        cat = sub_cat.category
        description = 'A fake god'
        unit_price = '1.23'
        data = {
            'user': user.pk,
            'name': name,
            'code': code,
            'description': description,
            'unit_price': unit_price,
            'unit': 'anything',
        }
        response2 = self.assertPOST200(
            url,
            follow=True,
            data={
                **data,
                self.EXTRA_CATEGORY_KEY: '',
            },
        )
        self.assertFormError(
            response2.context['form'],
            field=self.EXTRA_CATEGORY_KEY,
            errors=_('This field is required.'),
        )

        # ----
        response3 = self.client.post(
            url,
            follow=True,
            data={
                **data,

                self.EXTRA_CATEGORY_KEY: str(sub_cat.id),
            },
        )
        self.assertNoFormError(response3)

        product = self.get_alone_element(Product.objects.all())
        self.assertEqual(name,                product.name)
        self.assertEqual(code,                product.code)
        self.assertEqual(description,         product.description)
        self.assertEqual(Decimal(unit_price), product.unit_price)
        self.assertEqual(cat,                 product.category)
        self.assertEqual(sub_cat,             product.sub_category)

        self.assertRedirects(response3, product.get_absolute_url())

    def test_creation__images(self):
        "Images + credentials."
        user = self.login_as_basic_user(Product)

        create_image = partial(
            self._create_image, user=user,
            folder=Folder.objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)
        img_3 = create_image(ident=3, user=self.get_root_user())

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

                    self.EXTRA_CATEGORY_KEY: str(sub_cat.id),
                },
            )

        response1 = post(img_1, img_3)
        self.assertEqual(200, response1.status_code)
        self.assertFormError(
            response1.context['form'],
            field='images',
            errors=_('Some entities are not linkable: {}').format(img_3),
        )

        # ---
        response2 = post(img_1, img_2)
        self.assertNoFormError(response2)

        product = self.get_object_or_fail(Product, name=name)
        self.assertCountEqual([img_1, img_2], product.images.all())

    def test_edition(self):
        user = self.login_as_root_and_get()

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

                self.EXTRA_CATEGORY_KEY: str(product.sub_category.pk),
            },
        )
        self.assertNoFormError(response)

        product = self.refresh(product)
        self.assertEqual(name,                product.name)
        self.assertEqual(Decimal(unit_price), product.unit_price)

    def test_listview(self):
        user = self.login_as_root_and_get()

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
        self.assertCountEqual(products, products_page.object_list)

    def test_add_images(self):
        user = self.login_as_basic_user(Product)

        create_image = partial(
            self._create_image, user=user,
            folder=Folder.objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)
        img_3 = create_image(ident=3)
        img_4 = create_image(ident=4, user=self.get_root_user())
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
            response2.context['form'],
            field='images',
            errors=_('Some entities are not linkable: {}').format(img_4),
        )

        # ---
        response3 = post(img_1, img_2)
        self.assertNoFormError(response3)
        self.assertCountEqual([img_1, img_2, img_3], product.images.all())

        # ---
        img_5 = create_image(ident=5, user=user)
        response4 = post(img_1, img_5)
        self.assertEqual(200, response4.status_code)
        self.assertFormError(
            response4.context['form'],
            field='images',
            errors=_('«%(entity)s» violates the constraints.') % {'entity': img_1},
        )

    def test_add_images__bad_type(self):
        "Related is not a Product."
        user = self.login_as_root_and_get()
        rei = FakeContact.objects.create(user=user, first_name='Rei', last_name='Ayanami')
        self.assertGET404(reverse('products__add_images_to_product', args=(rei.id,)))

    def test_remove_image(self):
        user = self.login_as_standard(
            allowed_apps=['documents', 'products'],
            creatable_models=[Document],
        )
        creds = SetCredentials.objects.create(
            role=user.role,
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

    def test_remove_image__workflow(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='No images')

        source = workflows.EditedEntitySource(model=Product)
        Workflow.objects.create(
            title='Created Organisations are cool',
            content_type=Product,
            trigger=workflows.EntityEditionTrigger(model=Product),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=Product,
                        operator=operators.IsEmptyOperator,
                        field_name='images',
                        values=[True],
                    ),
                ],
            ),
            actions=[workflows.PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        img = self._create_image(ident=1, user=user)
        sub_cat = SubCategory.objects.first()
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )
        product.images.set([img])

        self.assertPOST200(
            reverse('products__remove_image', args=(product.id,)),
            data={'id': img.id}, follow=True,
        )
        self.assertFalse([*product.images.all()])
        self.assertHasProperty(entity=product, ptype=ptype)
