from functools import partial

from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from creme.creme_core.core.setting_key import SettingKey, SettingKeyRegistry

from ..base import CremeTestCase


class SettingKeyTestCase(CremeTestCase):
    def test_registry_register(self):
        sk1 = SettingKey(
            id='creme_core-test_sk_string',
            description='Page title',
            app_label='creme_core',
            type=SettingKey.STRING,
            blank=True,
        )
        sk2 = SettingKey(
            id='creme_core-test_sk_int',
            description='Page size',
            app_label='creme_core',
            type=SettingKey.INT, hidden=False,
        )
        sk3 = SettingKey(
            id='creme_core-test_sk_bool',
            description='Page hidden',
            app_label='creme_core',
            type=SettingKey.BOOL,
        )

        registry = SettingKeyRegistry()
        registry.register(sk1, sk2, sk3)

        # ------
        with self.assertNoException():
            sk = registry[sk1.id]
        self.assertEqual(sk1, sk)

        self.assertEqual(sk2, registry[sk2.id])
        self.assertEqual(sk3, registry[sk3.id])

        # ------
        all_key_ids = {sk.id for sk in registry}
        self.assertIn(sk1.id, all_key_ids)
        self.assertIn(sk2.id, all_key_ids)
        self.assertIn(sk3.id, all_key_ids)

        # ------
        registry.unregister(sk1, sk3)

        self.assertEqual(sk2, registry[sk2.id])

        with self.assertRaises(KeyError):
            registry[sk1.id]  # NOQA

        with self.assertRaises(KeyError):
            registry[sk3.id]  # NOQA

        all_key_ids = {sk.id for sk in registry}
        self.assertIn(sk2.id, all_key_ids)
        self.assertNotIn(sk1.id, all_key_ids)
        self.assertNotIn(sk3.id, all_key_ids)

        with self.assertRaises(registry.RegistrationError):
            registry.unregister(sk3)

    def test_registry_register_with_duplicate(self):
        sk1 = SettingKey(
            id='creme_core-test_sk_string',
            description='Page title',
            app_label='creme_core',
            type=SettingKey.STRING,
            blank=True,
        )
        sk2 = SettingKey(
            id=sk1.id,  # <===
            description='Page size',
            app_label='creme_core',
            type=SettingKey.INT,
            hidden=False,
        )

        registry = SettingKeyRegistry()
        registry.register(sk1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(sk2)

    def test_description(self):
        sk = SettingKey(
            id='creme_core-test_sk_string',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.STRING,
        )

        self.assertEqual('Short description', sk.description)
        self.assertEqual('Short description', sk.description_html)

        sk = SettingKey(
            id='creme_core-test_sk_string',
            description=(
                'This is a long,\n'
                'multiline,\n'
                '<a href="">escaped</a>\n'
                'and boring description\n'
            ),
            app_label='creme_core',
            type=SettingKey.STRING,
        )

        self.assertEqual(
            'This is a long,\n'
            'multiline,\n'
            '<a href="">escaped</a>\n'
            'and boring description\n',
            sk.description,
        )
        self.assertEqual(
            'This is a long,<br/>'
            'multiline,<br/>'
            '&lt;a href=&quot;&quot;&gt;escaped&lt;/a&gt;<br/>'
            'and boring description<br/>',
            sk.description_html,
        )

    def test_string(self):
        sk = SettingKey(
            id='creme_core-test_sk_string',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.STRING,
        )
        self.assertIs(sk.blank, False)
        self.assertIs(sk.hidden, False)

        value1 = 'foobar'
        self.assertEqual(value1, sk.cast(value1))
        self.assertEqual(value1, sk.value_as_html(value1))

        value2 = 'baz'
        self.assertEqual(value2, sk.cast(value2))
        self.assertEqual(value2, sk.value_as_html(value2))

        # ---
        ffield = sk.formfield()
        self.assertIsInstance(ffield, forms.CharField)
        self.assertEqual(_('Value'), ffield.label)
        self.assertTrue(ffield.required)
        self.assertIsInstance(ffield.widget, forms.Textarea)
        self.assertTrue(ffield.widget.is_required)

    def test_int(self):
        sk = SettingKey(
            id='creme_core-test_sk_int',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.INT,
        )
        self.assertEqual(123, sk.cast('123'))
        self.assertEqual(456, sk.cast('456'))

        self.assertRaises(ValueError, sk.cast, 'nan')

        # ---
        with override_language('en'):
            self.assertEqual('789',   sk.value_as_html(789))
            self.assertEqual('42',    sk.value_as_html(42))
            self.assertEqual('1,234', sk.value_as_html(1234))

        with override_language('fr'):
            self.assertEqual('789', sk.value_as_html(789))
            self.assertEqual('42',  sk.value_as_html(42))
            self.assertEqual('1 234', sk.value_as_html(1234))

        # ---
        ffield = sk.formfield()
        self.assertIsInstance(ffield, forms.IntegerField)
        self.assertEqual(_('Value'), ffield.label)
        self.assertTrue(ffield.required)

    def test_bool(self):
        sk = SettingKey(
            id='creme_core-test_sk_bool',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.BOOL,
        )
        self.assertIs(sk.cast(True),  True)
        self.assertIs(sk.cast(False), False)

        self.assertIs(sk.cast('1'), True)  # Not really useful test...

        # ---
        self.assertEqual(
            f'<input type="checkbox" checked disabled/>{_("Yes")}',
            sk.value_as_html(True),
        )

        # ---
        ffield = sk.formfield()
        self.assertIsInstance(ffield, forms.BooleanField)
        self.assertFalse(ffield.required)

    def test_hour(self):
        sk = SettingKey(
            id='creme_core-test_sk_hour',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.HOUR,
        )
        self.assertEqual(8, sk.cast('8'))
        self.assertEqual(22, sk.cast('22'))

        self.assertRaises(ValueError, sk.cast, 'nan')
        # self.assertRaises(ValueError, sk.cast, '24')  # TODO?

        # ---
        self.assertEqual(
            _('{hour}h').format(hour=8),
            sk.value_as_html('8'),
        )

        # ---
        ffield = sk.formfield()
        self.assertIsInstance(ffield, forms.IntegerField)
        self.assertEqual(0, ffield.min_value)
        self.assertEqual(23, ffield.max_value)

    def test_email(self):
        sk = SettingKey(
            id='creme_core-test_sk_email',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.EMAIL,
        )
        value1 = 'foo@bar.com'
        self.assertEqual(value1, sk.cast(value1))

        value2 = 'baz@stuuf.org'
        self.assertEqual(value2, sk.cast(value2))

        # self.assertRaises(ValueError, sk.cast, 'not_email')  # TODO?

        self.assertEqual(value1, sk.value_as_html(value1))
        self.assertIsInstance(sk.formfield(), forms.EmailField)

    def test_formfield_required(self):
        sk = SettingKey(
            id='creme_core-test_sk_int',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.INT,
        )
        self.assertFalse(sk.blank)
        self.assertTrue(sk.formfield().required)

        sk.blank = True
        self.assertFalse(sk.formfield().required)

    def test_custom_formfield(self):
        choices = [('1', 'One'), ('2', 'Two'), ('3', 'Three')]
        sk = SettingKey(
            id='creme_core-test_sk_int',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.INT,
            formfield_class=partial(forms.TypedChoiceField, choices=choices, coerce=int),
        )
        ffield = sk.formfield()
        self.assertIsInstance(ffield, forms.TypedChoiceField)
        self.assertEqual(choices, ffield.choices)
        self.assertEqual(2, ffield.clean('2'))

    def test_custom_renderer(self):
        choices = {'1': 'One', '2': 'Two'}
        sk = SettingKey(
            id='creme_core-test_sk_int',
            description='Short description',
            app_label='creme_core',
            type=SettingKey.INT,
            html_printer=lambda value: choices.get(value, '??'),
        )
        self.assertEqual('One', sk.value_as_html('1'))
        self.assertEqual('Two', sk.value_as_html('2'))
        self.assertEqual('??',  sk.value_as_html('3'))

# TODO: test unregister
