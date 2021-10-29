# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from creme.creme_core.models import FakeContact, SearchConfigItem
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import FakeOrganisation, FakeSector


class CremeSearchTagsTestCase(CremeTestCase):
    def test_search_form01(self):
        user = self.create_user()
        get_ct = ContentType.objects.get_for_model
        contact_ct_id = get_ct(FakeContact).id

        with self.assertNoException():
            render = Template(
                r'{% load creme_search %}'
                r'{% search_form user=user selected_ct_id=ct_id search_terms=terms %}'
            ).render(Context({
                'user': user,
                'terms': ['Acme', 'super2000'],
                'ct_id': contact_ct_id,
            }))

        tree = self.get_html_tree(render)

        input_node = self.get_html_node_or_fail(tree, './/input[@name="research"]')
        self.assertEqual("['Acme', 'super2000']", input_node.attrib.get('value'))
        self.assertEqual('3', input_node.attrib.get('minlength'))

        select_node = self.get_html_node_or_fail(tree, './/select[@name="ct_id"]')
        choices = [
            (option_node.attrib.get('value'), option_node.text)
            for option_node in select_node.findall('.//option')
        ]
        self.assertInChoices(
            value=str(contact_ct_id),
            label='Test Contact',
            choices=choices,
        )
        self.assertInChoices(
            value=str(get_ct(FakeOrganisation).id),
            label='Test Organisation',
            choices=choices,
        )
        self.assertNotInChoices(
            value=str(get_ct(FakeSector).id),
            choices=choices,
        )

        self.assertListEqual(
            [str(contact_ct_id)],
            [
                option_node.attrib.get('value')
                for option_node in select_node.findall('.//option[@selected=""]')
            ]
        )

    def test_search_form02(self):
        user = self.create_user()

        SearchConfigItem.objects.create_if_needed(
            model=FakeContact,
            fields=(),
            role='superuser',
            disabled=True,
        )

        get_ct = ContentType.objects.get_for_model
        contact_ct_id = get_ct(FakeContact).id

        with self.assertNoException():
            render = Template(
                r'{% load creme_search %}'
                r'{% search_form user=user selected_ct_id=None search_terms=terms %}'
            ).render(Context({
                'user': user,
                'terms': ['Acme', 'super2000'],
            }))

        tree = self.get_html_tree(render)

        select_node = self.get_html_node_or_fail(tree, './/select[@name="ct_id"]')
        choices = [
            (option_node.attrib.get('value'), option_node.text)
            for option_node in select_node.findall('.//option')
        ]
        self.assertNotInChoices(
            value=str(contact_ct_id),
            choices=choices,
        )
        self.assertInChoices(
            value=str(get_ct(FakeOrganisation).id),
            label='Test Organisation',
            choices=choices,
        )
