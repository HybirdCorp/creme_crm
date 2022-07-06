################################################################################
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
################################################################################

import random

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generates a new SECRET_KEY which can be used in your settings file.'
    requires_system_checks = []

    def handle(self, **options):
        # Code based on django/utils/crypto.py
        try:
            choice = random.SystemRandom().choice
        except NotImplementedError:
            from getpass import getpass
            from hashlib import sha256
            from time import time

            from django.utils.encoding import force_str  # force_text

            choice = random.choice

            self.stderr.write('No secure pseudo-random number generator is available.')
            self.stdout.write('Please enter a random sequence of chars.')

            while 1:
                kb_seed = getpass('At least 16 chars:').strip()

                if len(kb_seed) < 16:
                    self.stderr.write('The (stripped) strings must contain at least 16 chars.')
                else:
                    break

            random.seed(
                sha256(
                    f'{random.getstate()}{time()}{force_str(kb_seed)}'.encode()
                ).digest()
            )

        # List of chars copied from django/core/management/commands/startproject.py
        return ''.join(
            choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
            for _i in range(50)
        )
