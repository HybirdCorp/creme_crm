# -*- coding: utf-8 -*-

from creme.creme_core.core.setting_key import SettingKey, _SettingKeyRegistry

from ..base import CremeTestCase


class SettingKeyTestCase(CremeTestCase):
    def test_register(self):
        sk1 = SettingKey('creme_core-test_sk_string',
                         description='Page title',
                         app_label='creme_core',
                         type=SettingKey.STRING,
                         blank=True,
                        )
        sk2 = SettingKey('creme_core-test_sk_int',
                         description='Page size',
                         app_label='creme_core',
                         type=SettingKey.INT, hidden=False,
                        )
        sk3 = SettingKey('creme_core-test_sk_bool',
                         description='Page hidden',
                         app_label='creme_core',
                         type=SettingKey.BOOL,
                        )

        registry = _SettingKeyRegistry()
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
            __ = registry[sk1.id]

        with self.assertRaises(KeyError):
            __ = registry[sk3.id]

        all_key_ids = {sk.id for sk in registry}
        self.assertIn(sk2.id, all_key_ids)
        self.assertNotIn(sk1.id, all_key_ids)
        self.assertNotIn(sk3.id, all_key_ids)

        with self.assertRaises(registry.RegistrationError):
            registry.unregister(sk3)

    def test_duplicate(self):
        sk1 = SettingKey('creme_core-test_sk_string',
                         description='Page title',
                         app_label='creme_core',
                         type=SettingKey.STRING,
                         blank=True,
                        )
        sk2 = SettingKey(sk1.id,  # <===
                         description='Page size',
                         app_label='creme_core',
                         type=SettingKey.INT, hidden=False,
                        )

        registry = _SettingKeyRegistry()
        registry.register(sk1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(sk2)
