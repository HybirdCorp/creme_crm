# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

try:
    import random

    from creme_core.tests.base import CremeTestCase

    from creme_config.models import SettingValue, SettingKey

    from activesync.cipher import Cipher
except Exception as e:
    print 'Error:', e


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
        skey_id = 'CipherTestCase-test_ciphered_setting_value01'
        skey = SettingKey.objects.create(id=skey_id, type=SettingKey.STRING)
        sv = SettingValue.objects.get_or_create(key=skey, user=self.user)[0]
        self.assertEqual(1, SettingValue.objects.count())

        sv.value = Cipher.encrypt_for_db(password)
        sv.save()

        sv = SettingValue.objects.get(key=skey, user=self.user)
        self.assertEqual(password, Cipher.decrypt_from_db(sv.value))
