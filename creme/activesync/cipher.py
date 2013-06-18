# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

import base64
from Crypto.Cipher import AES

from django.conf import settings


class Cipher(object):
    @staticmethod
    def get_cipher():
        iv = ''.join(chr(0) for i in xrange(16))
        return AES.new(settings.SECRET_KEY[:32], AES.MODE_CFB, iv)

    @staticmethod
    def encrypt(text):
        return Cipher.get_cipher().encrypt(text)

    @staticmethod
    def decrypt(ciphered):
        return Cipher.get_cipher().decrypt(ciphered)

    @staticmethod
    def encrypt_for_db(text):
        """Cipher the text and encode it in base64. Indeed, ciphered string can't be directly saved in db
        because of encodings issues"""
        return base64.b64encode(Cipher.encrypt(text))

    @staticmethod
    def decrypt_from_db(ciphered):
        """base64 Decode the ciphered string and un-cipher it."""
        return Cipher.decrypt(base64.b64decode(ciphered))

