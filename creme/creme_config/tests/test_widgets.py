from collections import namedtuple

from creme.creme_config.forms.fields import MenuEntriesField
from creme.creme_config.forms.widgets import (
    ButtonMenuEditionWidget,
    MenuEditionWidget,
)
from creme.creme_core.gui.menu import Separator1Entry
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_menu import (
    FakeContactCreationEntry,
    FakeContactsEntry,
)

Option = namedtuple('Option', ['id', 'verbose_name', 'description'])


class ButtonMenuEditionWidgetTestCase(CremeTestCase):
    def test_init(self):
        widget = ButtonMenuEditionWidget(choices=((1, 'a'), (2, 'b')))
        self.assertEqual(widget.choices, [(1, 'a'), (2, 'b')])

    def test_create_option(self):
        test_button = Option("test_ButtonMenuEditWidget", 'VERBOSE NAME', "DESCRIPTION")
        widget = ButtonMenuEditionWidget()
        option = widget.create_option(
            name='NAME',
            button_id=test_button.id,
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
        choices = ((o.id, o) for o in options)
        widget = ButtonMenuEditionWidget(choices=choices)

        options = widget.create_options(
            name='N', value=['I4', 'I0']  # order matters
        )

        expected_options = [
            {'name': 'N', 'value': 'I1', 'label': 'VN1', 'description': 'D1', 'selected': False},
            {'name': 'N', 'value': 'I2', 'label': 'VN2', 'description': 'D2', 'selected': False},
            {'name': 'N', 'value': 'I3', 'label': 'VN3', 'description': 'D3', 'selected': False},
            {'name': 'N', 'value': 'I4', 'label': 'VN4', 'description': 'D4', 'selected': True},
            {'name': 'N', 'value': 'I0', 'label': 'VN0', 'description': 'D0', 'selected': True},

        ]
        self.assertListEqual(options, expected_options)


class MenuEditionWidgetTestCase(CremeTestCase):
    def test_init01(self):
        "Default parameters."
        widget = MenuEditionWidget()
        self.assertListEqual([],  widget.extra_entry_creators)
        self.assertTupleEqual((), widget.regular_entry_choices)

        name = 'my_widget'
        self.assertDictEqual(
            {
                'widget': {
                    'name': name,
                    'attrs': {},
                    'is_hidden': False,
                    'required': False,

                    'template_name': 'creme_config/forms/widgets/menu-editor.html',
                    'value': '[]',

                    'extra_creators': [],
                    'regular_entry_choices': [],
                },
            },
            widget.get_context(name=name, value='[]', attrs=None),
        )

    def test_init02(self):
        "With parameters."
        creator = MenuEntriesField.EntryCreator(
            label='Create a separator', entry_class=Separator1Entry,
        )

        entry1 = FakeContactsEntry()
        entry2 = FakeContactCreationEntry()

        def choices():
            yield entry1.id, entry1.label
            yield entry2.id, entry2.label

        widget = MenuEditionWidget(
            regular_entry_choices=choices(),
            extra_entry_creators=[creator],
        )
        self.assertListEqual([creator], widget.extra_entry_creators)

        ctxt = widget.get_context(name='name', value='[]', attrs=None)['widget']
        self.assertListEqual([creator], ctxt.get('extra_creators'))
        self.assertCountEqual(
            [
                (entry1.id, entry1.label),
                (entry2.id, entry2.label),
            ],
            ctxt.get('regular_entry_choices'),
        )
