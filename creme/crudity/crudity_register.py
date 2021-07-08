# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.conf import settings

from .fetchers import filesystem as fs_fetchers
from .fetchers import pop
from .inputs import email as email_inputs
from .inputs import filesystem as fs_inputs

fetchers = {
    'email':      [pop.PopFetcher],
    'filesystem': [fs_fetchers.FileSystemFetcher],
}
inputs = {
    'email': [
        email_inputs.CreateEmailInput,
        email_inputs.CreateInfopathInput,
    ],
    'filesystem': [fs_inputs.IniFileInput],
}
backends = []


if settings.TESTS_ON:
    from .tests import fake_crudity_register

    fetchers.update(fake_crudity_register.fetchers)
    inputs.update(fake_crudity_register.inputs)
    backends.extend(fake_crudity_register.backends)
