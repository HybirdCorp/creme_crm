# -*- coding: utf-8 -*-

from collections import namedtuple

from creme.creme_config.forms.widgets import ButtonMenuEditionWidget
from creme.creme_core.tests.base import CremeTestCase

Option = namedtuple("Option", ['id_', 'verbose_name', 'description'])


class ButtonMenuEditionWidgetTestCase(CremeTestCase):
    def test_init(self):
        widget = ButtonMenuEditionWidget(choices=((1, 'a'), (2, 'b')))
        self.assertEqual(widget.choices, [(1, 'a'), (2, 'b')])

    def test_create_option(self):
        test_button = Option("test_ButtonMenuEditWidget", 'VERBOSE NAME', "DESCRIPTION")
        widget = ButtonMenuEditionWidget()
        option = widget.create_option(
            name="NAME",
            button_id=test_button.id_,
            button=test_button,
            selected=True,
        )
        expected_option = {
            'name': 'NAME',
            'value': 'test_ButtonMenuEditWidget',
            'label': 'VERBOSE NAME',
            'description': 'DESCRIPTION',
            'selected': True,
        }
        self.assertDictEqual(option, expected_option)

    def test_create_options(self):
        options = [Option(f'I{i}', f'VN{i}', f'D{i}') for i in range(5)]
        choices = ((o.id_, o) for o in options)
        widget = ButtonMenuEditionWidget(choices=choices)

        options = widget.create_options(
            name="N", value=["I4", "I0"]  # order matters
        )

        expected_options = [
            {'name': 'N', 'value': 'I1', 'label': 'VN1', 'description': 'D1', 'selected': False},
            {'name': 'N', 'value': 'I2', 'label': 'VN2', 'description': 'D2', 'selected': False},
            {'name': 'N', 'value': 'I3', 'label': 'VN3', 'description': 'D3', 'selected': False},
            {'name': 'N', 'value': 'I4', 'label': 'VN4', 'description': 'D4', 'selected': True},
            {'name': 'N', 'value': 'I0', 'label': 'VN0', 'description': 'D0', 'selected': True},

        ]
        self.assertListEqual(options, expected_options)
