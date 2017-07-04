# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from .fetchers.pop import PopFetcher  # pop_fetcher
from .inputs import email


# fetchers = {'email': [pop_fetcher]}
fetchers = {'email': [PopFetcher]}
# inputs = {'email': [email.create_email_input, email.create_infopath_input]}
inputs = {'email': [email.CreateEmailInput, email.CreateInfopathInput]}
backends = []


if settings.TESTS_ON:
    from .tests import fake_crudity_register

    fetchers.update(fake_crudity_register.fetchers)
    inputs.update(fake_crudity_register.inputs)
    backends.extend(fake_crudity_register.backends)
