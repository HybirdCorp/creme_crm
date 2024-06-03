from json import dumps as json_dump

from django.utils.translation import gettext as _

from creme.creme_core.forms.batch_process import BatchActionsField

from ..base import CremeTestCase
from ..fake_models import FakeContact, FakeEmailCampaign


class BatchActionsFieldTestCase(CremeTestCase):
    @staticmethod
    def build_data(name, operator, value):
        return json_dump([{'name': name, 'operator': operator, 'value': value}])

    def test_clean_empty_required(self):
        field = BatchActionsField(required=True)
        msg = _('This field is required.')
        self.assertFormfieldError(field=field, value=None, messages=msg, codes='required')
        self.assertFormfieldError(field=field, value='', messages=msg, codes='required')
        self.assertFormfieldError(field=field, value='[]', messages=msg, codes='required')

    def test_clean_empty_not_required(self):
        field = BatchActionsField(required=False)
        self.assertNoException(field.clean, None)

    def test_clean_invalid_data_type(self):
        field = BatchActionsField()
        msg = _('Invalid type')
        self.assertFormfieldError(
            field=field, value='"this is a string"', messages=msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field, value='"{}"', messages=msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field,
            value='{"foobar":{"operator": "3", "name": "first_name"}}',
            messages=msg, codes='invalidtype',
        )
        self.assertFormfieldError(
            field=field, value='1', messages=msg, codes='invalidtype',
        )  # Not iterable

    def test_clean_incomplete_data_required(self):
        field = BatchActionsField(model=FakeContact)

        # No name
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, value='[{"operator": "upper"}]', messages=msg, codes='required',
        )

        # No operator
        self.assertFormfieldError(
            field=field, value='[{"name": "first_name"}]', messages=msg, codes='required',
        )

        # Value has no 'value' key
        self.assertFormfieldError(
            field=field,
            value='[{"operator": "upper", "name": "first_name"}]',
            messages=msg, codes='required',
        )

    def test_clean_invalid_field01(self):
        field = BatchActionsField(model=FakeContact)
        msg = _('This field is invalid with this model.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=self.build_data(
                name='boobies_size',  # <---
                operator='upper',
                value='',
            ),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=self.build_data(
                name='header_filter_search_field',  # Not editable
                operator='upper',
                value='',
            ),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidfield',
            value=self.build_data(
                name='civility',  # Type not managed
                operator='upper',
                value='',
            ),
        )

    def test_clean_invalid_field02(self):
        field = BatchActionsField(model=FakeEmailCampaign)
        self.assertFormfieldError(
            field=field,
            messages=_('This field is invalid with this model.'),
            codes='invalidfield',
            value=self.build_data(
                name='type',  # <---
                operator='add_int',
                value='5',
            ),
        )

    def test_clean_invalid_operator01(self):
        field = BatchActionsField(model=FakeContact)
        msg = _('This operator is invalid.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidoperator',
            value=self.build_data(
                name='first_name',
                operator='unknown_op',  # <--
                value='',
            ),
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='invalidoperator',
            value=self.build_data(
                name='first_name',
                operator='add_int',  # Apply to int, not str
                value='5',
            ),
        )

    def test_value_required(self):
        self.assertFormfieldError(
            field=BatchActionsField(model=FakeContact),
            value=self.build_data(
                name='first_name', operator='suffix',
                value='',  # <===
            ),
            messages=_('Invalid value => %(error)s') % {
                'error': _("The operator '{}' needs a value.").format(_('Suffix')),
            },
            codes='invalidvalue',
        )

    def test_value_typeerror(self):
        self.assertFormfieldError(
            field=BatchActionsField(model=FakeContact),
            value=self.build_data(
                name='first_name', operator='rm_start',
                value='notanint',  # <===
            ),
            messages=_('Invalid value => %(error)s') % {
                'error': _('{operator}: {message}.').format(
                    operator=_('Remove the start (N characters)'),
                    message=_('enter a whole number'),
                ),
            },
            codes='invalidvalue',
        )

    def test_ok01(self):
        with self.assertNumQueries(0):
            field = BatchActionsField(model=FakeContact)

        actions = field.clean(
            self.build_data(name='description', operator='upper', value='')
        )
        self.assertEqual(1, len(actions))

        contact = FakeContact(
            first_name='faye', last_name='Valentine', description='yarglaaaaaaaaaaa',
        )
        actions[0](contact)
        self.assertEqual('YARGLAAAAAAAAAAA', contact.description)

    def test_ok02(self):
        "Several actions."
        with self.assertNumQueries(0):
            field = BatchActionsField()
            field.model = FakeContact

        actions = field.clean(json_dump([
            {'name': 'first_name', 'operator': 'prefix', 'value': 'My '},
            {'name': 'last_name',  'operator': 'upper',  'value': ''},
        ]))
        self.assertEqual(2, len(actions))

        contact = FakeContact(first_name='Faye', last_name='Valentine')
        for action in actions:
            action(contact)

        self.assertEqual('My Faye',   contact.first_name)
        self.assertEqual('VALENTINE', contact.last_name)
