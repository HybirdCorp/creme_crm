from django.urls import reverse

from creme.creme_core.bricks import PropertiesBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import CustomEntity1  # NOQA
from creme.creme_core.models import CustomEntity2  # NOQA
from creme.creme_core.models import CustomEntityType

from ..base import CremeTestCase
# from .base import ButtonTestCaseMixin
from .base import BrickTestCaseMixin


# class EntityFilterViewsTestCase(BrickTestCaseMixin, ButtonTestCaseMixin, CremeTestCase):
class CustomEntityTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_detailview(self):
        user = self.login_as_root_and_get()
        CustomEntityType.objects.create(number=1, name='Training')

        ent = CustomEntity1.objects.create(user=user, name='Training 01')

        url = ent.get_absolute_url()
        self.assertEqual(
            reverse('creme_core__view_custom_entity', args=(1, ent.id,)),
            url,
        )

        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/view_entity.html')

        # TODO?
        # -----
        # last_item = self.get_alone_element(LastViewedItem.get_all(self.FakeRequest(user)))
        # self.assertEqual(fox.id,             last_item.pk)
        # self.assertEqual(fox.entity_type_id, last_item.ctype_id)
        # self.assertEqual(url,                last_item.url)
        # self.assertEqual(str(fox),           last_item.name)
        #
        # # -----
        # imprint = self.get_alone_element(Imprint.objects.all())
        # self.assertEqual(imprint.entity.get_real_entity(), fox)

        # -----
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=PropertiesBrick)
        self.get_brick_node(tree, brick=MODELBRICK_ID)

        bar_node = self.get_brick_node(tree, brick=Brick.GENERIC_HAT_BRICK_ID)
        title_node = self.get_html_node_or_fail(bar_node, ".//div[@class='bar-title']/h1")
        self.assertEqual(
            # TODO: name in DB
            f'Custom entity1 : {ent.name}',
            title_node.text.strip(),
        )

    def test_detailview__other_type(self):
        user = self.login_as_root_and_get()
        CustomEntityType.objects.create(number=2, name='Store')

        ent = CustomEntity2.objects.create(user=user, name='Store 01')

        url = ent.get_absolute_url()
        self.assertEqual(
            reverse('creme_core__view_custom_entity', args=(2, ent.id,)),
            url,
        )

        response = self.assertGET200(url)

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=Brick.GENERIC_HAT_BRICK_ID,
        )
        title_node = self.get_html_node_or_fail(brick_node, ".//div[@class='bar-title']/h1")
        self.assertEqual(
            # TODO: name in DB
            f'Custom entity2 : {ent.name}',
            title_node.text.strip(),
        )

    def test_detailview__disabled_type(self):
        user = self.login_as_root_and_get()
        # CustomEntityType.objects.create(...)  # NOPE

        ent = CustomEntity1.objects.create(user=user, name='Store 01')
        self.assertGET404(ent.get_absolute_url())

    # TODO: detailview with specific configuration for brick/buttons
