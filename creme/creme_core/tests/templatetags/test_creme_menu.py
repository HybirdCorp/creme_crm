from copy import deepcopy

from django.conf import settings
from django.template import Context, Template
from django.test.utils import override_settings
from django.utils.safestring import mark_safe

from creme.creme_core.gui import button_menu
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.menu import ContainerEntry, CustomURLEntry
from creme.creme_core.models import (
    ButtonMenuItem,
    FakeContact,
    FakeOrganisation,
    MenuConfigItem,
    UserRole,
)

from ..base import CremeTestCase


class MenuDisplayTestCase(CremeTestCase):
    css_class_prefix = 'ui-creme-navigation-item'

    def _render(self, user):
        with self.assertNoException():
            template = Template(
                r'{% load creme_menu %}'
                r'{% menu_display %}'
            )
            render = template.render(Context({
                'request': self.build_request(user=user),
                'user': user,
                'TIME_ZONE': 'Groland/Mufflin',
            }))

        return render

    def _assert_vanilla_menu(self, tree):
        # import xml.etree.ElementTree as ET
        # ET.dump(tree)

        class_prefix = self.css_class_prefix
        creme_li_node = tree.find(
            f".//li[@class='{class_prefix}-level0 {class_prefix}-id_creme_core-creme']"
        )
        self.assertIsNotNone(creme_li_node)
        self.assertEqual(settings.SOFTWARE_LABEL, creme_li_node.text)

        home_li_node = creme_li_node.find(
            f".//li[@class='{class_prefix}-level1 {class_prefix}-id_creme_core-home']"
        )
        self.assertIsNotNone(home_li_node)

    def _assert_no_vanilla_config(self, tree):
        class_prefix = self.css_class_prefix
        self.assertIsNone(tree.find(
            f".//li[@class='{class_prefix}-level0 {class_prefix}-id_creme_core-creme']"
        ))

    def _assert_custom_url_entry(self, container_node, url):
        class_prefix = self.css_class_prefix
        url_li_node = container_node.find(
            f".//li[@class='{class_prefix}-level1 {class_prefix}-id_creme_core-custom_url']"
        )
        self.assertIsNotNone(url_li_node)

        url_anchor_node = url_li_node.find('.//a')
        self.assertIsNotNone(url_anchor_node)
        self.assertEqual(url, url_anchor_node.attrib.get('href'))

    def _assert_no_container(self, tree, label):
        class_prefix = self.css_class_prefix
        for container in tree.findall(
            f".//li[@class='{class_prefix}-level0 {class_prefix}-id_creme_core-container']"
        ):
            if container.text == label:
                self.fail(f'A container named "{label}" has been unexpectedly found.')

    def _create_role_config(self, role, container_label, url):
        create_mitem = MenuConfigItem.objects.create
        container = create_mitem(
            role=role,
            entry_id=ContainerEntry.id,
            entry_data={'label': container_label},
            order=1,
        )
        create_mitem(
            role=role,
            entry_id=CustomURLEntry.id,
            order=1,
            parent=container,
            entry_data={'label': f'Mastodon ({role})', 'url': url},
        )

    def _create_superuser_config(self, container_label, url):
        create_mitem = MenuConfigItem.objects.create
        container = create_mitem(
            superuser=True,
            entry_id=ContainerEntry.id,
            entry_data={'label': container_label},
            order=1,
        )
        create_mitem(
            superuser=True,
            entry_id=CustomURLEntry.id,
            order=1,
            parent=container,
            entry_data={'label': 'Micro-blog', 'url': url},
        )

    def _get_containers(self, tree, length):
        class_prefix = self.css_class_prefix
        containers = tree.findall(
            f".//li[@class='{class_prefix}-level0 {class_prefix}-id_creme_core-container']"
        )
        self.assertEqual(length, len(containers))

        return containers

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_regular_config01(self):
        "Logged as superuser."
        user = self.create_user()
        render = self._render(user)
        self._assert_vanilla_menu(self.get_html_tree(render))

    @override_settings(SOFTWARE_LABEL='Amazing CRM')
    def test_regular_config02(self):
        "Logged as not super-user."
        create_role = UserRole.objects.create
        role1 = create_role(name='Developer')
        role2 = create_role(name='Salesman')

        user = self.create_user(role=role1)

        super_container_label = 'My super directory'
        self._create_superuser_config(  # Should not be used
            container_label=super_container_label,
            url='https://mastodon.mycompagny.org',
        )

        role2_container_label = f'Directory ({role2})'
        self._create_role_config(  # Should not be used
            role=role2,
            container_label=f'Directory ({role2})',
            url='https://mastodon2.mycompagny.com',
        )

        render = self._render(user)
        tree = self.get_html_tree(render)
        self._assert_vanilla_menu(tree)
        self._assert_no_container(tree, label=role2_container_label)
        self._assert_no_container(tree, label=super_container_label)

    def test_superuser_config(self):
        user = self.create_user()

        container_label = 'My super directory'
        url = 'https://mastodon.mycompagny.org'
        self._create_superuser_config(container_label=container_label, url=url)

        render = self._render(user)
        tree = self.get_html_tree(render)
        self._assert_no_vanilla_config(tree)

        containers = self._get_containers(tree, length=1)
        container_li_node = containers[0]
        self.assertEqual(container_label, container_li_node.text)
        self._assert_custom_url_entry(container_node=container_li_node, url=url)

    def test_role_config(self):
        create_role = UserRole.objects.create
        role1 = create_role(name='Developer')
        role2 = create_role(name='Salesman')

        user = self.create_user(role=role1)

        container_label = f'My directory ({role1})'
        url = 'https://mastodon1.mycompagny.com'
        self._create_role_config(
            role=role1,
            container_label=container_label,
            url=url,
        )
        self._create_role_config(
            role=role2,
            container_label=f'Directory ({role2})',
            url='https://mastodon2.mycompagny.com',
        )

        render = self._render(user)
        tree = self.get_html_tree(render)
        self._assert_no_vanilla_config(tree)

        containers = self._get_containers(tree, length=1)
        container_li_node = containers[0]
        self.assertEqual(container_label, container_li_node.text)
        self._assert_custom_url_entry(container_node=container_li_node, url=url)


class _TestButton(Button):
    action_id = 'creme_core-tests-dosomethingawesome1'

    def render(self, context):
        return mark_safe(
            f' <a class="menu_button" data-action="{self.action_id}" href="#"></a>'
        )


class TestButton01(_TestButton):
    # id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu01')
    id = Button.generate_id('creme_core', 'test_ttags_creme_menu01')
    action_id = 'creme_core-tests-dosomethingawesome01'


class TestButton02(_TestButton):
    # id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu02')
    id = Button.generate_id('creme_core', 'test_ttags_creme_menu02')
    action_id = 'creme_core-tests-dosomethingawesome02'


class TestButton03(_TestButton):
    # id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu03')
    id = Button.generate_id('creme_core', 'test_ttags_creme_menu03')
    action_id = 'creme_core-tests-dosomethingawesome03'


class TestButton04(_TestButton):
    # id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu04')
    id = Button.generate_id('creme_core', 'test_ttags_creme_menu04')
    action_id = 'creme_core-tests-dosomethingawesome04'


class TestButton05(_TestButton):
    # id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu05')
    id = Button.generate_id('creme_core', 'test_ttags_creme_menu05')
    action_id = 'creme_core-tests-dosomethingawesome05'


class MenuButtonsDisplayTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._original_button_registry = button_menu.button_registry
        cls.button_registry = button_registry = deepcopy(button_menu.button_registry)
        button_registry.register(
            TestButton01,
            TestButton02,
            TestButton03,
            TestButton04,
            TestButton05,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        button_menu.brick_registry = cls._original_button_registry

    def setUp(self):
        super().setUp()
        button_menu.button_registry = self.button_registry = deepcopy(self.button_registry)

    @staticmethod
    def get_button_nodes(tree):
        for li_node in tree.findall('.//li'):
            for node in li_node.findall('.//a'):
                if 'menu_button' in node.attrib.get('class').split():
                    yield node

    def test_menu_buttons_display01(self):
        user = self.create_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create_if_needed
        create_button(button=TestButton01, order=1)
        create_button(button=TestButton02, order=102, model=FakeOrganisation)
        create_button(button=TestButton03, order=101, model=FakeOrganisation)
        create_button(button=TestButton04, order=102, model=FakeContact)

        with self.assertNoException():
            template = Template(
                r'{% load creme_menu %}'
                r'{% menu_buttons_display %}'
            )
            render = template.render(Context({'user': user, 'object': orga}))

        # print(render)
        data_actions = {
            node.attrib.get('data-action'): i
            for i, node in enumerate(self.get_button_nodes(self.get_html_tree(render)))
        }

        def assertInButtons(action_id):
            index = data_actions.get(action_id)
            if index is None:
                self.fail(f'action_id={action_id} not found in {data_actions.keys()}')

            return index

        index1 = assertInButtons(TestButton01.action_id)
        index2 = assertInButtons(TestButton02.action_id)
        index3 = assertInButtons(TestButton03.action_id)
        self.assertLess(index1, index2)
        self.assertLess(index1, index3)
        self.assertLess(index3, index2)
        self.assertNotIn(TestButton04.action_id, data_actions)
        self.assertNotIn(TestButton05.action_id, data_actions)

    def test_menu_buttons_display02(self):
        "A button present in default config & ContentType's one => not duplicated."
        user = self.create_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create_if_needed
        create_button(button=TestButton01, order=1)
        create_button(button=TestButton02, order=101, model=FakeOrganisation)
        create_button(button=TestButton01, order=102, model=FakeOrganisation)

        with self.assertNoException():
            template = Template(
                r'{% load creme_menu %}'
                r'{% menu_buttons_display %}'
            )
            render = template.render(Context({'user': user, 'object': orga}))

        # print(render)
        actions_ids = []
        for node in self.get_button_nodes(self.get_html_tree(render)):
            action_id = node.attrib.get('data-action')
            if action_id in (TestButton01.action_id, TestButton02.action_id):
                actions_ids.append(action_id)

        self.assertListEqual(
            [TestButton01.action_id, TestButton02.action_id],
            actions_ids,
        )
