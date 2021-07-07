# -*- coding: utf-8 -*-

import json
from functools import partial

from django.utils.translation import gettext as _

from creme.creme_core.core.setting_key import (
    SettingKey,
    UserSettingKey,
    setting_key_registry,
    user_setting_key_registry,
)
from creme.creme_core.models import SettingValue
from creme.creme_core.tests.base import (
    CremeTestCase,
    OverrideSettingValueContext,
)
from creme.creme_core.utils import bool_as_html


class SettingValueTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self._registered_skey = []

    def tearDown(self):
        super().tearDown()
        setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, skey):
        setting_key_registry.register(skey)
        self._registered_skey.append(skey)

    def test_type_string(self):
        sk = SettingKey(
            'creme_core-test_model_string',
            description='Page title',
            app_label='creme_core', type=SettingKey.STRING, hidden=False,
        )
        self._register_key(sk)

        title = 'May the source be with you'
        sv = SettingValue(key=sk)
        sv.value = title
        sv.save()

        self.assertEqual(title, self.refresh(sv).value)

    def test_type_int(self):
        sk = SettingKey(
            id='persons-test_model_int', description='Page size',
            app_label='persons', type=SettingKey.INT,
        )
        self.assertFalse(sk.hidden)
        self.assertFalse(sk.blank)

        self._register_key(sk)

        size = 156
        sv = SettingValue(key=sk)
        sv.value = size
        sv.save()

        sv = self.refresh(sv)
        self.assertEqual(size, sv.value)
        self.assertEqual(size, sv.as_html)

        # ---
        size += 1
        sv.value = str(size)
        self.assertEqual(size, sv.value)

    def test_type_bool(self):
        self.login()

        sk = SettingKey(
            id='activities-test_model_bool', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)
        sv.value = True
        sv.save()

        sv = self.refresh(sv)
        self.assertIs(sv.value, True)
        self.assertHTMLEqual(
            '<input type="checkbox" checked disabled/>{}'.format(_('Yes')),
            sv.as_html,
        )

        sv.value = False
        sv.save()

        sv = self.refresh(sv)
        self.assertIs(sv.value, False)
        self.assertHTMLEqual(
            '<input type="checkbox" disabled/>{}'.format(_('No')),
            sv.as_html,
        )

    def test_type_hour(self):
        self.login()

        sk = SettingKey(
            id='persons-test_model_hour', description='Reminder hour',
            app_label='persons', type=SettingKey.HOUR,
        )
        self._register_key(sk)

        hour = 9
        sv = SettingValue(key=sk)
        sv.value = hour
        sv.save()

        sv = self.refresh(sv)
        self.assertEqual(hour, sv.value)
        self.assertEqual(_('{hour}h').format(hour=hour), sv.as_html)

    def test_type_email(self):
        self.login()

        sk = SettingKey(
            id='persons-test_model_email', description='Campaign Sender',
            app_label='emails', type=SettingKey.EMAIL,
        )
        self._register_key(sk)

        email = 'd.knut@eswat.ol'
        sv = SettingValue(key=sk)
        sv.value = email
        sv.save()

        sv = self.refresh(sv)
        self.assertEqual(email, sv.value)
        self.assertEqual(email, sv.as_html)

    def test_blank(self):
        sk = SettingKey(
            'creme_core-test_model_blank',
            description='API key',
            app_label='creme_core',
            type=SettingKey.STRING,
            blank=True,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)
        sv.value = ''
        sv.save()

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)
        self.assertEqual('', sv.as_html)

        sv.value = None
        self.assertIsNone(sv.value)

    def test_not_blank(self):
        sk = SettingKey(
            'creme_core-test_model_not_blank',
            description='API key',
            app_label='creme_core',
            type=SettingKey.STRING,
            blank=False,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)

        with self.assertRaises(ValueError):
            sv.value = None
            # sv.value = '' # TODO

        value = '111'

        with self.assertNoException():
            sv.value = value

        with self.assertRaises(ValueError):
            sv.value = None

        self.assertEqual(value, sv.value)

    def test_bad_value(self):
        sk = SettingKey(
            id='persons-test_bad_value', description='Page size',
            app_label='persons', type=SettingKey.INT,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)

        with self.assertRaises(ValueError):
            sv.value = 'abc'

    def test_get_4_key01(self):
        "Key ID."
        sk = SettingKey(
            id='activities-test_get_4_key01', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)
        sv.value = True
        sv.save()

        pk = sv.pk

        with self.assertNumQueries(1):
            sv = SettingValue.objects.get_4_key(sk.id)

        self.assertIsInstance(sv, SettingValue)
        self.assertEqual(pk, sv.pk)

        # Cache
        with self.assertNumQueries(0):
            sv = SettingValue.objects.get_4_key(sk.id)

        self.assertEqual(pk, sv.pk)

    def test_get_4_key02(self):
        "Key instance."
        sk = SettingKey(
            id='activities-test_get_4_key02', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)
        sv.value = True
        sv.save()

        pk = sv.pk

        with self.assertNumQueries(1):
            sv = SettingValue.objects.get_4_key(sk)

        self.assertIsInstance(sv, SettingValue)
        self.assertEqual(pk, sv.pk)

    def test_get_4_key03(self):
        "Exceptions."
        sk = SettingKey(
            id='activities-test_get_4_key03', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )
        self._register_key(sk)

        with self.assertRaises(KeyError):
            SettingValue.objects.get_4_key('unknown')

        with self.assertLogs(level='CRITICAL') as log_cm:
            with self.assertRaises(SettingValue.DoesNotExist):
                SettingValue.objects.get_4_key(sk)

        messages = log_cm.output
        self.assertEqual(1, len(messages))
        self.assertIn(''"creme_populate"'', messages[0])

    def test_get_4_key04(self):
        "Default value."
        sk = SettingKey(
            id='activities-test_get_4_key04', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )

        with self.assertLogs(level='CRITICAL') as log_cm:
            sv = SettingValue.objects.get_4_key(sk, default=False)

        messages = log_cm.output
        self.assertEqual(1, len(messages))
        self.assertIn('creme_populate', messages[0])

        self.assertEqual(sk.id, sv.key_id)
        self.assertIs(False, sv.value)

    def test_get_4_keys01(self):
        sk1 = SettingKey(
            id='activities-test_get_4_keys01_1', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )
        sk2 = SettingKey(
            id='activities-test_get_4_keys02_2', description='Logo size',
            app_label='activities', type=SettingKey.INT,
        )
        self._register_key(sk1)
        self._register_key(sk2)

        def create_svalue(skey, value):
            sv = SettingValue(key=skey)
            sv.value = value
            sv.save()

            return sv

        stored_sv1 = create_svalue(sk1, True)
        stored_sv2 = create_svalue(sk2, 100)

        pk1 = stored_sv1.pk
        pk2 = stored_sv2.pk

        with self.assertNumQueries(1):
            svalues = SettingValue.objects.get_4_keys(
                {'key': sk1.id},  # <= Key ID
                {'key': sk2},     # <= Key instance
            )

        self.assertIsInstance(svalues, dict)
        self.assertEqual(2, len(svalues))

        sv1 = svalues.get(sk1.id)
        self.assertIsInstance(sv1, SettingValue)
        self.assertEqual(pk1, sv1.pk)

        sv2 = svalues.get(sk2.id)
        self.assertEqual(pk2, sv2.pk)

        # Cache
        with self.assertNumQueries(0):
            svalues = SettingValue.objects.get_4_keys({'key': sk1.id})
        self.assertEqual(pk1, svalues[sk1.id].pk)

        # Cache (shared with get_4_key() )
        with self.assertNumQueries(0):
            sv2 = SettingValue.objects.get_4_key(sk2.id)
        self.assertEqual(pk2, sv2.pk)

    def test_get_4_keys02(self):
        "Exceptions."
        sk = SettingKey(
            id='activities-test_get_4_key02_1', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )
        self._register_key(sk)

        with self.assertRaises(KeyError):
            SettingValue.objects.get_4_keys({'key': 'unknown'})

        with self.assertLogs(level='CRITICAL') as log_cm:
            with self.assertRaises(SettingValue.DoesNotExist):
                SettingValue.objects.get_4_keys({'key': sk})

        messages = log_cm.output
        self.assertEqual(1, len(messages))
        self.assertIn(''"creme_populate"'', messages[0])

    def test_get_4_keys03(self):
        "Default value."
        sk = SettingKey(
            id='activities-test_get_4_key03_1', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )

        with self.assertLogs(level='CRITICAL') as log_cm:
            svalues = SettingValue.objects.get_4_keys({'key': sk, 'default': False})

        messages = log_cm.output
        self.assertEqual(1, len(messages))
        self.assertIn('creme_populate', messages[0])

        sv = svalues.get(sk.id)
        self.assertEqual(sk.id, sv.key_id)
        self.assertIs(False, sv.value)


class SettingValueHelpersTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(SettingValueHelpersTestCase, cls).setUpClass()
        cls.SETTING_KEY = SettingKey(
            id='creme_core-test_setting',
            description='',
            app_label='creme_core',
        )
        cls.INTEGER_SETTING_KEY = SettingKey(
            id='creme_core-test_setting_int',
            description='',
            app_label='creme_core',
            type=SettingKey.INT,
        )

        setting_key_registry.register(cls.SETTING_KEY)
        setting_key_registry.register(cls.INTEGER_SETTING_KEY)

    @classmethod
    def tearDownClass(cls):
        super(SettingValueHelpersTestCase, cls).tearDownClass()

        setting_key_registry.unregister(cls.SETTING_KEY)
        setting_key_registry.unregister(cls.INTEGER_SETTING_KEY)

    def test_value_4_key_empty(self):
        self.assertIsNone(SettingValue.objects.value_4_key('creme_core-test_setting'))

    def test_value_4_key_default(self):
        self.assertEqual(
            'Default',
            SettingValue.objects.value_4_key('creme_core-test_setting', default='Default')
        )
        self.assertEqual(
            'Default',
            SettingValue.objects.value_4_key(self.SETTING_KEY, default='Default')
        )
        self.assertEqual(
            'Default',
            SettingValue.objects.value_4_key(self.INTEGER_SETTING_KEY, default='Default')
        )

    def test_value_4_key_filled(self):
        SettingValue.objects.get_or_create(
            key_id='creme_core-test_setting',
            defaults={'value': 'A'}
        )
        self.assertEqual(
            'A',
            SettingValue.objects.value_4_key('creme_core-test_setting', default='Default')
        )
        self.assertEqual(
            'A',
            SettingValue.objects.value_4_key(self.SETTING_KEY, default='Default')
        )

    def test_value_4_key_invalid_key(self):
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-unknown_setting'))

    def test_has_exists_4_key(self):
        self.assertFalse(SettingValue.objects.exists_4_key('creme_core-test_setting'))
        self.assertFalse(SettingValue.objects.exists_4_key('creme_core-unknown_setting'))

        SettingValue.objects.get_or_create(
            key_id='creme_core-test_setting',
            defaults={'value': 'A'}
        )

        self.assertTrue(SettingValue.objects.exists_4_key('creme_core-test_setting'))

    def test_set_4_key(self):
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-test_setting'))

        # create a new value
        SettingValue.objects.set_4_key('creme_core-test_setting', 'A')
        self.assertEqual('A', SettingValue.objects.get(key_id='creme_core-test_setting').value)
        self.assertEqual('A', SettingValue.objects.value_4_key('creme_core-test_setting'))

        # replace value and flush the cache
        SettingValue.objects.set_4_key('creme_core-test_setting', 'B')
        self.assertEqual('B', SettingValue.objects.get(key_id='creme_core-test_setting').value)
        self.assertEqual('B', SettingValue.objects.value_4_key('creme_core-test_setting'))

        # remove the value in database
        SettingValue.objects.set_4_key('creme_core-test_setting', None)
        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-test_setting'))

    def test_set_4_key_cast(self):
        SettingValue.objects.set_4_key('creme_core-test_setting_int', 12)
        self.assertEqual(12, SettingValue.objects.get(key_id='creme_core-test_setting_int').value)
        self.assertEqual(12, SettingValue.objects.value_4_key('creme_core-test_setting_int'))

    def test_set_4_key_invalid_key(self):
        with self.assertRaises(KeyError):
            SettingValue.objects.set_4_key('creme_core-unknown_setting', 'A')

    def test_set_4_key_invalid_cast(self):
        with self.assertRaises(Exception):
            SettingValue.objects.set_4_key('creme_core-test_setting_int', 'B')

        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-test_setting'))

        # integer can be cast a str
        SettingValue.objects.set_4_key('creme_core-test_setting', 12)
        self.assertEqual('12', SettingValue.objects.value_4_key('creme_core-test_setting'))

    def test_override_setting_value(self):
        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-test_setting'))

        with OverrideSettingValueContext('creme_core-test_setting', 'T'):
            self.assertEqual('T', SettingValue.objects.get(key_id='creme_core-test_setting').value)
            self.assertEqual('T', SettingValue.objects.value_4_key('creme_core-test_setting'))

            with OverrideSettingValueContext('creme_core-test_setting', 'U'):
                self.assertEqual(
                    'U', SettingValue.objects.get(key_id='creme_core-test_setting').value
                )
                self.assertEqual('U', SettingValue.objects.value_4_key('creme_core-test_setting'))

            self.assertEqual(
                'T', SettingValue.objects.get(key_id='creme_core-test_setting').value
            )
            self.assertEqual('T', SettingValue.objects.value_4_key('creme_core-test_setting'))

        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-test_setting'))

    def test_override_setting_value_invalid_key(self):
        with self.assertRaises(KeyError):
            with OverrideSettingValueContext('creme_core-unknown_setting', 'T'):
                pass

    def test_override_setting_value_invalid_cast(self):
        with self.assertRaises(Exception):
            with OverrideSettingValueContext('creme_core-test_setting_int', 'T'):
                pass

        self.assertFalse(
            SettingValue.objects.filter(key_id='creme_core-test_setting_int').exists()
        )
        self.assertEqual(None, SettingValue.objects.value_4_key('creme_core-test_setting_int'))


class UserSettingValueTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self._registered_skey = []

    def tearDown(self):
        super().tearDown()
        user_setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, *skeys):
        user_setting_key_registry.register(*skeys)
        self._registered_skey.extend(skeys)

    def test_basic(self):
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_string',
            description='Page title',
            app_label='creme_core',
            type=SettingKey.STRING, hidden=False,
        )
        self._register_key(sk)

        title = 'May the source be with you'
        settings = user.settings

        with self.assertRaises(KeyError):
            settings[sk]  # NOQA

        with self.assertRaises(settings.ReadOnlyError):
            settings[sk] = title

        with settings:
            settings[sk] = title

        with self.assertNoException():
            value = settings[sk]

        self.assertEqual(title, value)

        with self.assertNoException():
            value = user.settings[sk]

        self.assertEqual(title, value)

    def test_get(self):
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_string',
            description='Page title',
            app_label='creme_core',
            type=SettingKey.STRING, hidden=False,
        )
        self._register_key(sk)

        settings = user.settings

        with self.assertNoException():
            value = settings.get(sk)

        self.assertIsNone(value)

        with self.assertNoException():
            value = settings.get(sk, '')

        self.assertEqual('', value)

        title = 'May the source be with you'
        with self.assertRaises(settings.ReadOnlyError):
            settings[sk] = title

        with settings:
            settings[sk] = title

        self.assertEqual(title, settings.get(sk, ''))

    def test_serialise(self):
        "JSON in DB + int."
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_int',
            description='Page size',
            app_label='creme_core',
            type=SettingKey.INT, hidden=False,
        )
        self._register_key(sk)

        size = 142

        with user.settings as settings:
            settings[sk] = size

        # Oblige UserSettingValue to be stored in DB (we clean the cache)
        user = self.refresh(user)

        with self.assertNoException():
            value = user.settings.get(key=sk)

        self.assertEqual(size, value)

    def test_bool(self):
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_bool',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=False,
        )
        self._register_key(sk)

        def test_value(displayed):
            with user.settings as settings:
                settings[sk] = displayed

            with self.assertNoException():
                value = self.refresh(user).settings.get(key=sk)

            self.assertIs(displayed, value)

        test_value(True)
        test_value(False)

    def test_multi_save(self):
        user = self.create_user()

        build_key = partial(
            UserSettingKey, app_label='creme_core', type=SettingKey.INT, hidden=False,
        )
        sk1 = build_key('creme_core-test_model_int1', description='Page width')
        sk2 = build_key('creme_core-test_model_int2', description='Page height')
        self._register_key(sk1, sk2)

        width = 142
        height = 236

        with self.assertNumQueries(1):
            with user.settings as mngr:
                mngr[sk1] = width
                mngr[sk2] = height

        user = self.refresh(user)

        with self.assertNumQueries(0):
            get = user.settings.get
            value1 = get(key=sk1)
            value2 = get(key=sk2)

        self.assertEqual(width, value1)
        self.assertEqual(height, value2)

    def _aux_test_pop(self):
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_int',
            description='Page size',
            app_label='creme_core',
            type=SettingKey.INT, hidden=False,
        )
        self._register_key(sk)

        settings = user.settings
        with settings:
            settings[sk] = 142

        return user, settings, sk

    def test_pop01(self):
        user, settings, sk = self._aux_test_pop()

        with self.assertRaises(settings.ReadOnlyError):
            settings.pop(key=sk)

        with settings:
            value = settings.pop(sk)

        self.assertEqual(142, value)

        settings = self.refresh(user).settings
        self.assertIsNone(settings.get(sk))

        with self.assertRaises(KeyError):
            with settings:
                settings.pop(sk)

    def test_pop02(self):
        user, settings, sk = self._aux_test_pop()

        default = 42
        with settings:
            value = settings.pop(sk, default)

        self.assertEqual(142, value)

        settings = self.refresh(user).settings

        self.assertIsNone(settings.get(sk))

        with settings:
            value = settings.pop(sk, default)

        self.assertEqual(default, value)

    def test_cast_int(self):
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_int',
            description='Page size',
            app_label='creme_core',
            type=SettingKey.INT, hidden=False,
        )
        self._register_key(sk)

        size = 143

        with user.settings as settings:
            settings[sk] = str(size)  # <== __str()__

        self.assertEqual(size, user.settings.get(key=sk))

        user = self.refresh(user)
        self.assertEqual(size, user.settings.get(key=sk))

        with self.assertNoException():
            d = json.loads(user.json_settings)

        self.assertIsInstance(d, dict)
        self.assertIsInstance(d.get(sk.id), int)

    def test_cast_bool(self):
        user = self.create_user()

        sk = UserSettingKey(
            'creme_core-test_model_bool',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=False,
        )
        self._register_key(sk)

        displayed = 1

        with user.settings as settings:
            settings[sk] = displayed

        self.assertIs(True, user.settings.get(key=sk))

        # -----
        displayed = 0

        with user.settings as settings:
            settings[sk] = displayed

        self.assertIs(False, user.settings.get(key=sk))

        # -----
        user = self.refresh(user)

        with self.assertNoException():
            d = json.loads(user.json_settings)

        self.assertIsInstance(d, dict)
        self.assertIsInstance(d.get(sk.id), bool)

    def test_as_html(self):
        user = self.create_user()

        sk1 = UserSettingKey(
            'creme_core-test_model_bool',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=False,
        )
        sk2 = UserSettingKey(
            'creme_core-test_model_str',
            description='Page size',
            app_label='creme_core',
            type=SettingKey.STRING, hidden=False,
        )
        self._register_key(sk1, sk2)

        with self.assertRaises(KeyError):
            user.settings.as_html(sk1)

        str_value = 'Foobar'
        with user.settings as settings:
            settings[sk1] = True
            settings[sk2] = str_value

        as_html = user.settings.as_html
        self.assertEqual(bool_as_html(True), as_html(sk1))
        self.assertEqual(str_value,          as_html(sk2))
