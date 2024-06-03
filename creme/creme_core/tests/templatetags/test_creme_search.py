from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from creme.creme_core.models import (
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    FakeSector,
)
from creme.creme_core.tests.base import CremeTestCase


class CremeSearchTagsTestCase(CremeTestCase):
    def test_search_form01(self):
        get_ct = ContentType.objects.get_for_model
        contact_ct_id = get_ct(FakeContact).id

        with self.assertNoException():
            render = Template(
                r'{% load creme_search %}'
                r'{% search_form models=models selected_ct_id=ct_id search_terms=terms %}'
            ).render(Context({
                'models': [FakeContact, FakeOrganisation],
                'terms': ['Acme', 'super2000'],
                'ct_id': contact_ct_id,
            }))

        tree = self.get_html_tree(render)

        input_node = self.get_html_node_or_fail(tree, './/input[@name="search"]')
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
            value=str(get_ct(FakeDocument).id),
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
            ],
        )

    def test_search_form02(self):
        get_ct = ContentType.objects.get_for_model
        contact_ct_id = get_ct(FakeContact).id

        with self.assertNoException():
            render = Template(
                r'{% load creme_search %}'
                r'{% search_form models=models selected_ct_id=None search_terms=terms %}'
            ).render(Context({
                'models': [FakeOrganisation],
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
