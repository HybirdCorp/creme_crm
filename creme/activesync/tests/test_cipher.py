# -*- coding: utf-8 -*-

try:
    import random

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
    from creme.creme_core.models import SettingValue

    from ..cipher import Cipher
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class CipherTestCase(CremeTestCase):
    def setUp(self):
        super(CipherTestCase, self).setUp()
        self._registered_skey = []

    def tearDown(self):
        super(CipherTestCase, self).tearDown()
        setting_key_registry.unregister(*self._registered_skey)

    def _register_key(self, skey):
        setting_key_registry.register(skey)
        self._registered_skey.append(skey)

    def test_cipher01(self):
        text = "Creme is opensrc" # len(text) is explicitly == 16
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher02(self):
        text = "Creme" # len(text) is explicitly <= 16
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher03(self):
        text = "Creme is a free/open-source"  # len(text) is explicitly >= 16 and not mod 16
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

        text = ''.join(str(i) for i in xrange(50))
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher04(self):
        for i in xrange(143):
            # Test with text with not always the same length
            text = ''.join(chr(random.randint(0, 0xFF)) for _ in xrange(i))
            ciphertext = Cipher.encrypt(text)
            self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher05(self):
        for i in xrange(143):
            # Test with text with not always the same length
            text = ''.join(chr(random.randint(0, 255)) for _ in xrange(i))
            ciphertext = Cipher.encrypt(text)
            self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher_for_db01(self):
        text = "Creme is opensrc"
        ciphertext = Cipher.encrypt_for_db(text)
        self.assertEqual(text, Cipher.decrypt_from_db(ciphertext))

    def test_cipher_for_db02(self):
        for i in xrange(143):
            # Test with text with not always the same length
            text = ''.join(chr(random.randint(0, 255)) for _ in xrange(i))
            ciphertext = Cipher.encrypt_for_db(text)
            self.assertEqual(text, Cipher.decrypt_from_db(ciphertext))

    def test_ciphered_setting_value01(self):
        self.login()
        password = "my password"
        skey_id = 'activesync-test_ciphered_setting_value01'
        skey = SettingKey(id=skey_id, type=SettingKey.STRING, app_label='creme_config', description='')
        self._register_key(skey)

        sv = SettingValue.objects.get_or_create(key_id=skey_id, defaults={'value': 'val'})[0]
        sv.value = Cipher.encrypt_for_db(password)
        sv.save()

        sv = self.refresh(sv)
        self.assertEqual(password, Cipher.decrypt_from_db(sv.value))
