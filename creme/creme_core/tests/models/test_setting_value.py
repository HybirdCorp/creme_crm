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


class _SettingValueTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self._registered_skey = []

    def tearDown(self):
        super().tearDown()
        setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, skey):
        setting_key_registry.register(skey)
        self._registered_skey.append(skey)


class SettingValueTestCase(_SettingValueTestCase):
    def test_type_string(self):
        sk = SettingKey(
            id='creme_core-test_model_string',
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
        self.assertEqual(f'{size}', sv.as_html)

        # ---
        size += 1
        sv.value = str(size)
        self.assertEqual(size, sv.value)

    def test_type_bool(self):
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
            id='creme_core-test_model_blank',
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
        self.assertEqual('', sv.json_value)
        self.assertEqual('', sv.value)
        self.assertEqual('', sv.as_html)

        sv.value = None
        self.assertIsNone(sv.value)

    def test_not_blank(self):
        sk = SettingKey(
            id='creme_core-test_model_not_blank',
            description='API key',
            app_label='creme_core',
            type=SettingKey.STRING,
            blank=False,
        )
        self._register_key(sk)

        sv = SettingValue(key=sk)

        with self.assertRaises(ValueError):
            sv.value = ''

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


class SettingValueManagerTestCase(_SettingValueTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        super().tearDownClass()

        setting_key_registry.unregister(cls.SETTING_KEY)
        setting_key_registry.unregister(cls.INTEGER_SETTING_KEY)

    def test_get_4_key__key_id(self):
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

    def test_get_4_key__key_instance(self):
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

    def test_get_4_key__exceptions(self):
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

        message = self.get_alone_element(log_cm.output)
        self.assertIn(''"creme_populate"'', message)

    def test_get_4_key__default_value(self):
        sk = SettingKey(
            id='activities-test_get_4_key04', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )

        with self.assertLogs(level='CRITICAL') as log_cm:
            sv = SettingValue.objects.get_4_key(sk, default=False)

        message = self.get_alone_element(log_cm.output)
        self.assertIn('creme_populate', message)

        self.assertEqual(sk.id, sv.key_id)
        self.assertIs(False, sv.value)

    def test_get_4_keys(self):
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

        self.assertIsDict(svalues, length=2)

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

    def test_get_4_keys__exceptions(self):
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

        message = self.get_alone_element(log_cm.output)
        self.assertIn(''"creme_populate"'', message)

    def test_get_4_keys__default_value(self):
        sk = SettingKey(
            id='activities-test_get_4_key03_1', description='Display logo?',
            app_label='activities', type=SettingKey.BOOL,
        )

        with self.assertLogs(level='CRITICAL') as log_cm:
            svalues = SettingValue.objects.get_4_keys({'key': sk, 'default': False})

        message = self.get_alone_element(log_cm.output)
        self.assertIn('creme_populate', message)

        sv = svalues.get(sk.id)
        self.assertEqual(sk.id, sv.key_id)
        self.assertIs(False, sv.value)

    def test_value_4_key__empty(self):
        key_id = self.SETTING_KEY.id

        with self.assertLogs(level='CRITICAL') as logs_manager:
            self.assertIsNone(SettingValue.objects.value_4_key(key_id))
        self.assertIn(
            f'SettingValue with key_id="{key_id}" cannot be found!',
            logs_manager.output[0],
        )

    def test_value_4_key__default(self):
        def_val = 'Default'
        value_4_key = SettingValue.objects.value_4_key

        with self.assertLogs(level='CRITICAL'):
            self.assertEqual(
                def_val, value_4_key(self.SETTING_KEY.id, default=def_val),
            )
        with self.assertNoLogs(level='CRITICAL'):  # Default value => no log
            self.assertEqual(
                def_val, value_4_key(self.SETTING_KEY, default=def_val)
            )
        with self.assertLogs(level='CRITICAL'):
            self.assertEqual(
                def_val, value_4_key(self.INTEGER_SETTING_KEY, default=def_val),
            )

    def test_value_4_key__filled(self):
        key_id = self.SETTING_KEY.id
        SettingValue.objects.get_or_create(key_id=key_id, defaults={'value': 'A'})
        value_4_key = SettingValue.objects.value_4_key
        self.assertEqual('A', value_4_key(key_id,           default='Default'))
        self.assertEqual('A', value_4_key(self.SETTING_KEY, default='Default'))

    def test_value_4_key__invalid_key(self):
        self.assertIsNone(SettingValue.objects.value_4_key('creme_core-unknown_setting'))

    def test_has_exists_4_key(self):
        key_id = self.SETTING_KEY.id
        self.assertFalse(SettingValue.objects.exists_4_key(key_id))
        self.assertFalse(SettingValue.objects.exists_4_key('creme_core-unknown_setting'))

        SettingValue.objects.get_or_create(key_id=key_id, defaults={'value': 'A'})
        self.assertTrue(SettingValue.objects.exists_4_key(key_id))

    def test_set_4_key(self):
        key_id = self.SETTING_KEY.id
        with self.assertLogs(level='CRITICAL'):
            self.assertIsNone(SettingValue.objects.value_4_key(key_id))

        # Create a new value
        SettingValue.objects.set_4_key(key_id, 'A')
        self.assertEqual('A', SettingValue.objects.get(key_id=key_id).value)
        self.assertEqual('A', SettingValue.objects.value_4_key(key_id))

        # Replace value and flush the cache
        SettingValue.objects.set_4_key(key_id, 'B')
        self.assertEqual('B', SettingValue.objects.get(key_id=key_id).value)
        self.assertEqual('B', SettingValue.objects.value_4_key(key_id))

        # Remove the value in database
        SettingValue.objects.set_4_key(key_id, None)
        self.assertFalse(SettingValue.objects.filter(key_id=key_id).exists())
        with self.assertLogs(level='CRITICAL'):
            self.assertIsNone(SettingValue.objects.value_4_key(key_id))

    def test_set_4_key__cast(self):
        key_id = self.INTEGER_SETTING_KEY.id
        value = 12
        SettingValue.objects.set_4_key(key_id, value)
        self.assertEqual(value, SettingValue.objects.get(key_id=key_id).value)
        self.assertEqual(value, SettingValue.objects.value_4_key(key_id))

    def test_set_4_key__invalid_key(self):
        with self.assertRaises(KeyError):
            SettingValue.objects.set_4_key('creme_core-unknown_setting', 'A')

    def test_set_4_key__invalid_cast(self):
        with self.assertRaises(Exception):
            SettingValue.objects.set_4_key(self.INTEGER_SETTING_KEY.id, 'B')

        with self.assertRaises(Exception):
            SettingValue.objects.set_4_key(self.INTEGER_SETTING_KEY, 'other')

        key_id = self.SETTING_KEY.id
        self.assertFalse(SettingValue.objects.filter(key_id=key_id).exists())
        with self.assertLogs(level='CRITICAL'):
            self.assertIsNone(SettingValue.objects.value_4_key(key_id))

        # Integer can be cast a str
        SettingValue.objects.set_4_key(key_id, 12)
        self.assertEqual('12', SettingValue.objects.value_4_key(key_id))

    def test_override_setting_value(self):
        key_id = self.SETTING_KEY.id
        self.assertFalse(SettingValue.objects.filter(key_id=key_id).exists())

        SettingValue.objects.set_4_key(key_id, 'A')

        with OverrideSettingValueContext(key_id, 'T'):
            self.assertEqual('T', SettingValue.objects.get(key_id=key_id).value)
            self.assertEqual('T', SettingValue.objects.value_4_key(key_id))

            with OverrideSettingValueContext(key_id, 'U'):
                self.assertEqual('U', SettingValue.objects.get(key_id=key_id).value)
                self.assertEqual('U', SettingValue.objects.value_4_key(key_id))

            self.assertEqual('T', SettingValue.objects.get(key_id=key_id).value)
            self.assertEqual('T', SettingValue.objects.value_4_key(key_id))

        self.assertEqual('A', SettingValue.objects.value_4_key(key_id))

    def test_override_setting_value__no_value_in_db(self):
        key_id = self.SETTING_KEY.id
        self.assertFalse(SettingValue.objects.filter(key_id=key_id).exists())

        with OverrideSettingValueContext(key_id, 'T'):
            self.assertEqual('T', SettingValue.objects.get(key_id=key_id).value)
            self.assertEqual('T', SettingValue.objects.value_4_key(key_id))

            with OverrideSettingValueContext(key_id, 'U'):
                self.assertEqual('U', SettingValue.objects.get(key_id=key_id).value)
                self.assertEqual('U', SettingValue.objects.value_4_key(key_id))

            self.assertEqual('T', SettingValue.objects.get(key_id=key_id).value)
            self.assertEqual('T', SettingValue.objects.value_4_key(key_id))

        self.assertFalse(SettingValue.objects.filter(key_id=key_id).exists())
        with self.assertLogs(level='CRITICAL'):
            self.assertIsNone(SettingValue.objects.value_4_key(key_id))

    def test_override_setting_value__invalid_key(self):
        with self.assertRaises(KeyError):
            with OverrideSettingValueContext('creme_core-unknown_setting', 'T'):
                pass

    def test_override_setting_value__invalid_cast(self):
        key_id = self.INTEGER_SETTING_KEY.id
        SettingValue.objects.set_4_key(key_id, 12)

        with self.assertRaises(ValueError) as exc_mngr:
            with OverrideSettingValueContext(key_id, 'T'):
                self.assertEqual('T', SettingValue.objects.get(key_id=key_id).value)

        self.assertIn('invalid literal', str(exc_mngr.exception))


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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_string',
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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_string',
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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_int',
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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_bool',
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
        user = self.get_root_user()

        build_key = partial(
            UserSettingKey, app_label='creme_core', type=SettingKey.INT, hidden=False,
        )
        sk1 = build_key(id='creme_core-test_model_int1', description='Page width')
        sk2 = build_key(id='creme_core-test_model_int2', description='Page height')
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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_int',
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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_int',
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
        user = self.get_root_user()

        sk = UserSettingKey(
            id='creme_core-test_model_bool',
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
        user = self.get_root_user()

        sk1 = UserSettingKey(
            id='creme_core-test_model_bool',
            description='Page displayed',
            app_label='creme_core',
            type=SettingKey.BOOL, hidden=False,
        )
        sk2 = UserSettingKey(
            id='creme_core-test_model_str',
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
