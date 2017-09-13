# -*- coding: utf-8 -*-

try:
    from functools import partial
    import json

    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.core.setting_key import (SettingKey, UserSettingKey,
           setting_key_registry, user_setting_key_registry)
    from creme.creme_core.models import SettingValue
    from creme.creme_core.utils import bool_as_html
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class SettingValueTestCase(CremeTestCase):
    def setUp(self):
        super(SettingValueTestCase, self).setUp()
        self._registered_skey = []

    def tearDown(self):
        super(SettingValueTestCase, self).tearDown()
        setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, skey):
        setting_key_registry.register(skey)
        self._registered_skey.append(skey)

    def test_type_string(self):
        sk = SettingKey('creme_core-test_model_string',
                        description=u"Page title",
                        app_label='creme_core',
                        type=SettingKey.STRING, hidden=False,
                       )
        self._register_key(sk)

        title = 'May the source be with you'
        sv = SettingValue.objects.create(key=sk, user=None, value=title)

        self.assertEqual(title, self.refresh(sv).value)

    def test_type_int(self):
        sk = SettingKey(id='persons-test_model_int', description=u"Page size",
                        app_label='persons', type=SettingKey.INT,
                       )
        self.assertFalse(sk.hidden)
        self.assertFalse(sk.blank)

        self._register_key(sk)

        size = 156
        sv = SettingValue.objects.create(key=sk, user=None, value=size)

        sv = self.refresh(sv)
        self.assertEqual(size, sv.value)
        self.assertEqual(size, sv.as_html)

        # ---
        size += 1
        sv.value = str(size)
        self.assertEqual(size, sv.value)

    def test_type_bool(self):
        self.login()

        sk = SettingKey(id='activities-test_model_bool', description=u"Display logo ?",
                        app_label='activities', type=SettingKey.BOOL,
                       )
        self._register_key(sk)

        sv = SettingValue.objects.create(key=sk, user=self.user, value=True)

        sv = self.refresh(sv)
        self.assertIs(sv.value, True)
        self.assertEqual('<input type="checkbox" checked disabled/>%s' % _('Yes'), sv.as_html)

        sv.value = False
        sv.save()

        sv = self.refresh(sv)
        self.assertIs(sv.value, False)
        self.assertEqual('<input type="checkbox" disabled/>%s' % _('No'), sv.as_html)

    def test_type_hour(self):
        self.login()

        sk = SettingKey(id='persons-test_model_hour', description='Reminder hour',
                        app_label='persons', type=SettingKey.HOUR,
                       )
        self._register_key(sk)

        hour = 9
        sv = SettingValue.objects.create(key=sk, user=self.user, value=hour)

        sv = self.refresh(sv)
        self.assertEqual(hour, sv.value)
        self.assertEqual(_('%sh') % hour, sv.as_html)

    def test_type_email(self):
        self.login()

        sk = SettingKey(id='persons-test_model_email', description='Campaign Sender',
                        app_label='emails', type=SettingKey.EMAIL,
                       )
        self._register_key(sk)

        email = u'd.knut@eswat.ol'
        sv = SettingValue.objects.create(key=sk, user=self.user, value=email)

        sv = self.refresh(sv)
        self.assertEqual(email, sv.value)
        self.assertEqual(email, sv.as_html)

    def test_create_value_if_needed(self):
        self.login()

        sk = SettingKey(id='persons-test_create_value_if_needed', description=u"Page size",
                        app_label='persons', type=SettingKey.INT,
                       )
        self._register_key(sk)

        self.assertFalse(SettingValue.objects.filter(key_id=sk))

        size = 156
        sv = SettingValue.create_if_needed(key=sk, user=None, value=size)
        self.assertIsInstance(sv, SettingValue)
        self.assertIsNone(sv.user)
        self.assertEqual(size, sv.value)

        with self.assertNoException():
            self.refresh(sv)

        sv = SettingValue.create_if_needed(key=sk, user=None, value=size + 1)
        self.assertEqual(size, sv.value)  # Not a new size

    def test_blank(self):
        sk = SettingKey('creme_core-test_model_blank',
                        description=u'API key',
                        app_label='creme_core',
                        type=SettingKey.STRING,
                        blank=True,
                       )
        self._register_key(sk)

        sv = SettingValue.objects.create(key=sk, value='')

        sv = self.refresh(sv)
        self.assertEqual('', sv.value_str)
        self.assertIsNone(sv.value)
        self.assertEqual('', sv.as_html)

        sv.value = None
        self.assertIsNone(sv.value)

    def test_not_blank(self):
        sk = SettingKey('creme_core-test_model_not_blank',
                        description=u'API key',
                        app_label='creme_core',
                        type=SettingKey.STRING,
                        blank=False,
                       )
        self._register_key(sk)

        with self.assertRaises(ValueError):
            # SettingValue.objects.create(key=sk, value='')  TODO
            SettingValue.objects.create(key=sk, value=None)

        value = '111'
        sv = SettingValue.objects.create(key=sk, value=value)

        with self.assertRaises(ValueError):
            sv.value = None

        self.assertEqual(value, sv.value)

    def test_bad_value(self):
        sk = SettingKey(id='persons-test_bad_value', description=u'Page size',
                        app_label='persons', type=SettingKey.INT,
                       )
        self._register_key(sk)

        with self.assertRaises(ValueError):
            SettingValue.objects.create(key=sk, value='abc')


class UserSettingValueTestCase(CremeTestCase):
    def setUp(self):
        super(UserSettingValueTestCase, self).setUp()
        self._registered_skey = []

    def tearDown(self):
        super(UserSettingValueTestCase, self).tearDown()
        user_setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, *skeys):
        user_setting_key_registry.register(*skeys)
        self._registered_skey.extend(skeys)

    def test_basic(self):
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_string',
                            description=u'Page title',
                            app_label='creme_core',
                            type=SettingKey.STRING, hidden=False,
                           )
        self._register_key(sk)

        title = 'May the source be with you'
        settings = user.settings

        with self.assertRaises(KeyError):
            settings[sk]

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
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_string',
                            description=u'Page title',
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
        "JSON in DB + int"
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_int',
                            description=u'Page size',
                            app_label='creme_core',
                            type=SettingKey.INT, hidden=False,
                           )
        self._register_key(sk)

        size = 142

        with user.settings as settings:
            settings[sk] = size

        user = self.refresh(user)  # Oblige UserSettingValue to be stored in DB (we clean the cache)

        with self.assertNoException():
            value = user.settings.get(key=sk)

        self.assertEqual(size, value)

    def test_bool(self):
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_bool',
                            description=u'Page displayed',
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
        user = self.login()

        build_key = partial(UserSettingKey, app_label='creme_core',
                            type=SettingKey.INT, hidden=False,
                           )
        sk1 = build_key('creme_core-test_model_int1',
                        description=u'Page width',
                       )
        sk2 = build_key('creme_core-test_model_int2',
                        description=u'Page height',
                       )
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
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_int',
                            description=u'Page size',
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
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_int',
                            description=u'Page size',
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
        user = self.login()

        sk = UserSettingKey('creme_core-test_model_bool',
                            description=u'Page displayed',
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
        user = self.login()

        sk1 = UserSettingKey('creme_core-test_model_bool',
                             description=u'Page displayed',
                             app_label='creme_core',
                             type=SettingKey.BOOL, hidden=False,
                            )
        sk2 = UserSettingKey('creme_core-test_model_str',
                            description=u'Page size',
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

