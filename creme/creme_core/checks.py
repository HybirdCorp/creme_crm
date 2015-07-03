# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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
from django.core.checks import register, Error


class Tags(object):
    settings = 'settings'


@register(Tags.settings)
def check_secret_key(**kwargs):
    errors = []

    if settings.SECRET_KEY == '1&7rbnl7u#+j-2#@5=7@Z0^9v@y_Q!*y^krWS)r)39^M)9(+6(':
        errors.append(Error("You did not generate a secret key.",
                            hint='Change the SECRET_KEY setting in your'
                                 ' local_settings.py/project_settings.py',
                            obj='creme.creme_core',
                            id='creme.E002',
                           )
                     )

    return errors
