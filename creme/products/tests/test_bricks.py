from decimal import Decimal
from functools import partial

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.products.bricks import ImagesBrick
from creme.products.models import SubCategory

from .base import (
    Folder,
    Product,
    Service,
    _ProductsTestCase,
    skipIfCustomProduct,
    skipIfCustomService,
)


class ImagesBrickTestCase(BrickTestCaseMixin, _ProductsTestCase):
    @skipIfCustomProduct
    def test_product__no_image(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )
        response = self.assertGET200(product.get_absolute_url())

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=ImagesBrick,
        )
        self.assertEqual(_('Images'), self.get_brick_title(brick_node))

        buttons_node = self.get_brick_header_buttons(brick_node)
        self.assertBrickHeaderHasButton(
            buttons_node=buttons_node,
            url=reverse('products__add_images_to_product', args=(product.id,)),
            label=_('Add images'),
        )

        msg_node = self.get_html_node_or_fail(
            brick_node, './/div[@class="brick-tiles-empty"]',
        )
        self.assertEqual(_('No image for the moment'), msg_node.text)

    @skipIfCustomProduct
    def test_product__images(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        create_image = partial(
            self._create_image, user=user,
            folder=Folder.objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)

        product.images.set([img_1, img_2])

        ImagesBrick.page_size = max(4, settings.BLOCK_SIZE)  # TODO: revert?

        response = self.assertGET200(product.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=ImagesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2, title='{count} Image', plural_title='{count} Images',
        )
        self.get_html_node_or_fail(
            brick_node, f".//a[@href='{img_1.get_absolute_url()}']"
        )
        self.get_html_node_or_fail(
            brick_node, f".//a[@href='{img_2.get_absolute_url()}']"
        )

    @skipIfCustomService
    def test_service(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(
            user=user, name='Eva washing', reference='42', description='Blabla',
            unit_price=Decimal('1.23'),  unit='A wash',
            category=sub_cat.category, sub_category=sub_cat,
        )
        response = self.assertGET200(service.get_absolute_url())

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=ImagesBrick,
        )
        self.assertEqual(_('Images'), self.get_brick_title(brick_node))

        buttons_node = self.get_brick_header_buttons(brick_node)
        self.assertBrickHeaderHasButton(
            buttons_node=buttons_node,
            url=reverse('products__add_images_to_service', args=(service.id,)),
            label=_('Add images'),
        )
