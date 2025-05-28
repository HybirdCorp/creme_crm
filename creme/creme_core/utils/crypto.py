################################################################################
#
# Copyright (c) 2023-2025 Hybird
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
################################################################################

import base64

# from cryptography.fernet import Fernet, InvalidToken
# from cryptography.hazmat.primitives import hashes
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.utils.encoding import force_bytes


class SymmetricEncrypter:
    """From the cryptography's documentation:
    Fernet guarantees that a message encrypted using it cannot be manipulated or
    read without the key. Fernet is an implementation of symmetric (also known
    as “secret key”) authenticated cryptography.
    """
    class Error(Exception):
        pass

    def __init__(self, salt, secret=None):
        # NB: we load cryptography lazily because there are import issue (double import)
        #     in some environments (wsgi mode?).
        #     > ImportError: PyO3 modules do not yet support subinterpreters,
        #       see https://github.com/PyO3/pyo3/issues/576
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        if secret is None:
            secret = settings.SECRET_KEY

        salt = force_bytes(salt)
        secret = force_bytes(secret)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            # see django/contrib/auth/hashers.py
            iterations=1_000_000,
        )
        self.fernet = Fernet(key=base64.urlsafe_b64encode(kdf.derive(secret)))

    def encrypt(self, data: bytes) -> bytes:
        return self.fernet.encrypt(data)

    def decrypt(self, encrypted: bytes) -> bytes:
        from cryptography.fernet import InvalidToken

        try:
            return self.fernet.decrypt(encrypted)
        except InvalidToken as e:
            raise self.Error('SymmetricEncrypter.decrypt: invalid token') from e
