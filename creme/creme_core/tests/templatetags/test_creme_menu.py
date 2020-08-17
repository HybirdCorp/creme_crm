# -*- coding: utf-8 -*-

from copy import deepcopy

from bleach._vendor import html5lib
from django.template import Context, Template
from django.utils.safestring import mark_safe

from creme.creme_core.gui import button_menu
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.models import (
    ButtonMenuItem,
    FakeContact,
    FakeOrganisation,
)

from ..base import CremeTestCase


class _TestButton(Button):
    action_id = 'creme_core-tests-dosomethingawesome1'

    def render(self, context):
        return mark_safe(
            f' <a class="menu_button" data-action="{self.action_id}" href="#"></a>'
        )


class TestButton01(_TestButton):
    id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu01')
    action_id = 'creme_core-tests-dosomethingawesome01'


class TestButton02(_TestButton):
    id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu02')
    action_id = 'creme_core-tests-dosomethingawesome02'


class TestButton03(_TestButton):
    id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu03')
    action_id = 'creme_core-tests-dosomethingawesome03'


class TestButton04(_TestButton):
    id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu04')
    action_id = 'creme_core-tests-dosomethingawesome04'


class TestButton05(_TestButton):
    id_ = Button.generate_id('creme_core', 'test_ttags_creme_menu05')
    action_id = 'creme_core-tests-dosomethingawesome05'


# TODO: test menu_display()
class CremeMenuTagsTestCase(CremeTestCase):
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

    def get_html_tree(self, content):
        return html5lib.parse(content, namespaceHTMLElements=False)

    def get_button_nodes(self, tree):
        for li_node in tree.findall('.//li'):
            for node in li_node.findall('.//a'):
                if 'menu_button' in node.attrib.get('class').split():
                    yield node

    def test_menu_buttons_display01(self):
        user = self.create_user()
        orga = FakeOrganisation.objects.create(user=user, name='Nerv')

        create_button = ButtonMenuItem.objects.create_if_needed
        create_button(pk='test-button1', button=TestButton01, order=1)
        create_button(pk='test-button2', button=TestButton02, order=102, model=FakeOrganisation)
        create_button(pk='test-button3', button=TestButton03, order=101, model=FakeOrganisation)
        create_button(pk='test-button4', button=TestButton04, order=102, model=FakeContact)

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
        create_button(pk='test-button1', button=TestButton01, order=1)
        create_button(pk='test-button2', button=TestButton02, order=101, model=FakeOrganisation)
        create_button(pk='test-button3', button=TestButton01, order=102, model=FakeOrganisation)

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
