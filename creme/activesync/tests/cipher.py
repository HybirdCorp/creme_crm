# -*- coding: utf-8 -*-

try:
    import random

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.core.setting_key import SettingKey, setting_key_registry
    from creme.creme_core.models import SettingValue

    from ..cipher import Cipher
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class CipherTestCase(CremeTestCase):
    def test_cipher01(self):
        text = "Creme is opensrc" # len(text) is explicitly == 16
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher02(self):
        text = "Creme" # len(text) is explicitly <= 16
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher03(self):
        text = "Creme is a free/open-source" # len(text) is explicitly >= 16 and not mod 16
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

        text = "".join(str(i) for i in xrange(50))
        ciphertext = Cipher.encrypt(text)
        self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher04(self):
        for i in xrange(143):
            text = ''.join(chr(random.randint(0, 0xFF)) for i in xrange(i))#Test with text with not always the same length
            ciphertext = Cipher.encrypt(text)
            self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher05(self):
        for i in xrange(143):
            text = ''.join(chr(random.randint(0, 255)) for i in xrange(i))#Test with text with not always the same length
            ciphertext = Cipher.encrypt(text)
            self.assertEqual(text, Cipher.decrypt(ciphertext))

    def test_cipher_for_db01(self):
        text = "Creme is opensrc"
        ciphertext = Cipher.encrypt_for_db(text)
        self.assertEqual(text, Cipher.decrypt_from_db(ciphertext))

    def test_cipher_for_db02(self):
        for i in xrange(143):
            text = ''.join(chr(random.randint(0, 255)) for i in xrange(i))#Test with text with not always the same length
            ciphertext = Cipher.encrypt_for_db(text)
            self.assertEqual(text, Cipher.decrypt_from_db(ciphertext))

    def test_ciphered_setting_value01(self):
        self.login()
        password = "my password"
        skey_id = 'activesync-test_ciphered_setting_value01'
        skey = SettingKey(id=skey_id, type=SettingKey.STRING, app_label='creme_config', description='')
        setting_key_registry.register(skey) #TODO: clean in tearDown()...

        sv = SettingValue.create_if_needed(key=skey, user=self.user, value='val')
        self.assertEqual(1, SettingValue.objects.filter(key_id=skey_id).count())

        sv.value = Cipher.encrypt_for_db(password)
        sv.save()

        sv = SettingValue.objects.get(key_id=skey_id, user=self.user)
        self.assertEqual(password, Cipher.decrypt_from_db(sv.value))
