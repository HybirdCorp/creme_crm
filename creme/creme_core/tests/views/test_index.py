from copy import deepcopy
from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.bricks import (
    HistoryBrick,
    RecentEntitiesBrick,
    StatisticsBrick,
)
from creme.creme_core.gui.bricks import Brick, brick_registry
from creme.creme_core.models import BrickHomeLocation, BrickMypageLocation
from creme.creme_core.views.index import Home, MyPage

from ..base import CremeTestCase
from .base import AppPermissionBrick, BrickTestCaseMixin  # ViewsTestCase


class IndexViewsTestCase(BrickTestCaseMixin, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        assert hasattr(Home, 'brick_registry')
        assert hasattr(MyPage, 'brick_registry')
        Home.brick_registry = MyPage.brick_registry = deepcopy(brick_registry).register(
            AppPermissionBrick,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        delattr(Home, 'brick_registry')
        assert hasattr(Home, 'brick_registry')
        assert AppPermissionBrick.id not in Home.brick_registry._brick_classes

        delattr(MyPage, 'brick_registry')
        assert hasattr(MyPage, 'brick_registry')
        assert AppPermissionBrick.id not in MyPage.brick_registry._brick_classes

    @override_settings(SOFTWARE_LABEL='Creme')
    def test_home(self):
        self.login_as_root()
        response = self.assertGET200(reverse('creme_core__home'))
        self.assertTemplateUsed(response, 'creme_core/home.html')

        context = response.context
        self.assertEqual(
            reverse('creme_core__reload_home_bricks'),
            context.get('bricks_reload_url'),
        )

        bricks = context.get('bricks')
        # self.assertIsList(bricks, min_length=2)
        # self.assertIsInstance(bricks[0], Brick)
        self.assertIsDict(bricks, length=1)

        main_bricks = bricks.get('main')
        self.assertIsList(main_bricks, min_length=2)

        # self.assertIsInstance(bricks[0], Brick)
        self.assertIsInstance(main_bricks[0], Brick)

        # brick_ids = [b.id for b in bricks]
        brick_ids = [b.id for b in main_bricks]
        i_recent = self.assertIndex(RecentEntitiesBrick.id, brick_ids)
        i_stats = self.assertIndex(StatisticsBrick.id, brick_ids)
        i_history = self.assertIndex(HistoryBrick.id,    brick_ids)
        self.assertLess(i_recent, i_stats)
        self.assertLess(i_stats, i_history)

        self.assertContains(response, _('Home') + ' - Creme', html=True)

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_home__superuser_bricks_config(self):
        self.login_as_root()

        brick_id = StatisticsBrick.id
        BrickHomeLocation.objects.create(brick_id=brick_id, superuser=True, order=1)

        # Should not be used
        BrickHomeLocation.objects.create(
            brick_id=HistoryBrick.id, role=self.get_regular_role(), order=1,
        )

        response = self.assertGET200(reverse('creme_core__home'))
        bricks = response.context.get('bricks')
        # self.assertEqual(len(bricks), 1)
        self.assertIsDict(bricks, length=1)

        main_bricks = bricks.get('main')
        self.assertIsList(main_bricks, length=1)

        # brick = bricks[0]
        brick = main_bricks[0]
        self.assertIsInstance(brick, StatisticsBrick)
        self.assertEqual(brick_id, brick.id)

        self.assertContains(response, _('Home') + ' - My CRM', html=True)

    def test_home__role_bricks_config(self):
        user = self.login_as_standard()
        role2 = self.create_role(name='Viewer')

        brick_id = StatisticsBrick.id
        create_hbl = BrickHomeLocation.objects.create
        create_hbl(brick_id=brick_id, role=user.role, order=1)

        # Should not be used
        create_hbl(brick_id=HistoryBrick.id, superuser=True, order=1)
        create_hbl(brick_id=HistoryBrick.id, role=role2,     order=1)

        response = self.assertGET200(reverse('creme_core__home'))
        bricks = response.context.get('bricks')
        # self.assertEqual(len(bricks), 1)
        self.assertIsDict(bricks, length=1)

        main_bricks = bricks.get('main')
        self.assertIsList(main_bricks, length=1)

        # brick = bricks[0]
        brick = main_bricks[0]
        self.assertIsInstance(brick, StatisticsBrick)
        self.assertEqual(brick_id, brick.id)

    def test_home__permissions(self):
        user = self.login_as_standard()

        create_hbl = partial(BrickHomeLocation.objects.create, role=user.role)
        create_hbl(brick_id=StatisticsBrick.id,    order=1)
        create_hbl(brick_id=AppPermissionBrick.id, order=2)

        response = self.assertGET200(reverse('creme_core__home'))
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=StatisticsBrick)

        brick_node = self.get_brick_node(tree, brick=AppPermissionBrick)
        self.assertIn('brick-forbidden', brick_node.attrib.get('class'))
        self.assertEqual(AppPermissionBrick.verbose_name, self.get_brick_title(brick_node))

        content_node = self.get_html_node_or_fail(
            brick_node, './/div[@class="brick-content"]',
        )
        self.assertEqual(
            _('You are not allowed to view this block'),
            content_node.text.strip(),
        )

    def test_my_page(self):
        self.login_as_root()
        response = self.assertGET200(reverse('creme_core__my_page'))
        self.assertTemplateUsed(response, 'creme_core/my_page.html')

        context = response.context
        self.assertEqual(
            reverse('creme_core__reload_home_bricks'),
            context.get('bricks_reload_url'),
        )

        # bricks = context.get('bricks')
        # self.assertIsList(bricks)
        # self.assertIn(HistoryBrick, {b.__class__ for b in bricks})
        bricks = context.get('bricks')
        self.assertIsDict(bricks, length=1)

        main_bricks = bricks.get('main')
        self.assertIsList(main_bricks)
        self.assertIn(HistoryBrick, {b.__class__ for b in main_bricks})

    def test_my_page__permissions(self):
        user = self.login_as_standard()

        create_mbl = partial(BrickMypageLocation.objects.create, user=user)
        create_mbl(brick_id=StatisticsBrick.id,    order=1)
        create_mbl(brick_id=AppPermissionBrick.id, order=2)

        response = self.assertGET200(reverse('creme_core__my_page'))
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, brick=StatisticsBrick)

        brick_node = self.get_brick_node(tree, brick=AppPermissionBrick)
        self.assertIn('brick-forbidden', brick_node.attrib.get('class'))
        self.assertEqual(AppPermissionBrick.verbose_name, self.get_brick_title(brick_node))

        content_node = self.get_html_node_or_fail(
            brick_node, './/div[@class="brick-content"]',
        )
        self.assertEqual(
            _('You are not allowed to view this block'),
            content_node.text.strip(),
        )
