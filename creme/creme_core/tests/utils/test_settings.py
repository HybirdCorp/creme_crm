# -*- coding: utf-8 -*-

from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
from creme.creme_core.models.setting_value import SettingValue
from creme.creme_core.utils.settings import (
    TemporarySettingValueContext,
    get_setting_value,
    has_setting_value,
    set_setting_value,
)

from ..base import CremeTestCase


class SettingsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(SettingsTestCase, cls).setUpClass()
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
        super(SettingsTestCase, cls).tearDownClass()
        setting_key_registry.unregister(cls.SETTING_KEY)

    def test_get_setting_value_empty(self):
        self.assertEqual(None, get_setting_value('creme_core-test_setting'))

    def test_get_setting_value_default(self):
        self.assertEqual(
            'Default',
            get_setting_value('creme_core-test_setting', default='Default')
        )
        self.assertEqual(
            'Default',
            get_setting_value(self.SETTING_KEY, default='Default')
        )
        self.assertEqual(
            'Default',
            get_setting_value(self.INTEGER_SETTING_KEY, default='Default')
        )

    def test_get_setting_value_filled(self):
        SettingValue.objects.get_or_create(
            key_id='creme_core-test_setting',
            defaults={'value': 'A'}
        )
        self.assertEqual(
            'A',
            get_setting_value('creme_core-test_setting', default='Default')
        )
        self.assertEqual(
            'A',
            get_setting_value(self.SETTING_KEY, default='Default')
        )

    def test_get_setting_value_invalid_key(self):
        self.assertEqual(None, get_setting_value(None))
        self.assertEqual(None, get_setting_value('creme_core-unknown_setting'))

    def test_has_setting_value(self):
        self.assertFalse(has_setting_value('creme_core-test_setting'))
        self.assertFalse(has_setting_value('creme_core-unknown_setting'))
        self.assertFalse(has_setting_value(None))

        SettingValue.objects.get_or_create(
            key_id='creme_core-test_setting',
            defaults={'value': 'A'}
        )

        self.assertTrue(has_setting_value('creme_core-test_setting'))

    def test_set_setting_value(self):
        self.assertEqual(None, get_setting_value('creme_core-test_setting'))

        # create a new value
        set_setting_value('creme_core-test_setting', 'A')
        self.assertEqual('A', SettingValue.objects.get(key_id='creme_core-test_setting').value)
        self.assertEqual('A', get_setting_value('creme_core-test_setting'))

        # replace value and flush the cache
        set_setting_value('creme_core-test_setting', 'B')
        self.assertEqual('B', SettingValue.objects.get(key_id='creme_core-test_setting').value)
        self.assertEqual('B', get_setting_value('creme_core-test_setting'))

        # remove the value in database
        set_setting_value('creme_core-test_setting', None)
        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, get_setting_value('creme_core-test_setting'))

    def test_set_setting_value_cast(self):
        set_setting_value('creme_core-test_setting_int', 12)
        self.assertEqual(12, SettingValue.objects.get(key_id='creme_core-test_setting_int').value)
        self.assertEqual(12, get_setting_value('creme_core-test_setting_int'))

    def test_set_setting_value_invalid_key(self):
        with self.assertRaises(KeyError):
            set_setting_value(None, 'A')

        with self.assertRaises(KeyError):
            set_setting_value('creme_core-unknown_setting', 'A')

    def test_set_setting_value_invalid_cast(self):
        with self.assertRaises(Exception):
            set_setting_value('creme_core-test_setting_int', 'B')

        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, get_setting_value('creme_core-test_setting'))

        # integer can be cast a str
        set_setting_value('creme_core-test_setting', 12)
        self.assertEqual('12', get_setting_value('creme_core-test_setting'))

    def test_temporary_setting_value(self):
        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, get_setting_value('creme_core-test_setting'))

        with TemporarySettingValueContext('creme_core-test_setting', 'T'):
            self.assertEqual('T', SettingValue.objects.get(key_id='creme_core-test_setting').value)
            self.assertEqual('T', get_setting_value('creme_core-test_setting'))

            with TemporarySettingValueContext('creme_core-test_setting', 'U'):
                self.assertEqual(
                    'U', SettingValue.objects.get(key_id='creme_core-test_setting').value
                )
                self.assertEqual('U', get_setting_value('creme_core-test_setting'))

            self.assertEqual(
                'T', SettingValue.objects.get(key_id='creme_core-test_setting').value
            )
            self.assertEqual('T', get_setting_value('creme_core-test_setting'))

        self.assertFalse(SettingValue.objects.filter(key_id='creme_core-test_setting').exists())
        self.assertEqual(None, get_setting_value('creme_core-test_setting'))

    def test_temporary_setting_value_invalid_key(self):
        with self.assertRaises(KeyError):
            with TemporarySettingValueContext('creme_core-unknown_setting', 'T'):
                pass

    def test_fake_setting_value_invalid_cast(self):
        with self.assertRaises(Exception):
            with TemporarySettingValueContext('creme_core-test_setting_int', 'T'):
                pass

        self.assertFalse(
            SettingValue.objects.filter(key_id='creme_core-test_setting_int').exists()
        )
        self.assertEqual(None, get_setting_value('creme_core-test_setting_int'))
