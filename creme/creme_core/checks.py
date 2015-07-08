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
    api_breaking = 'api_breaking'


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

# TODO: remove me in Creme 1.7
@register(Tags.api_breaking)
def check_creme_core_registers(**kwargs):
    from imp import find_module

    from django.apps import apps

    errors = []

    # We search the remaining 'creme_core_register.py' files of all apps.
    for app_config in apps.get_app_configs():
        app_name = app_config.name

        try:
            find_module('creme_core_register',
                        __import__(app_name, {}, {}, [app_config.label]).__path__,
                       )
        except ImportError:
            pass # There is no creme_core_register.py => OK
        else:
            errors.append(Error('You seem to still use the "creme_core_register" feature.',
                            hint='Use the AppConfig feature instead & remove the '
                                 'creme_core_register.py(c) file(s)',
                            obj=app_name,
                            id='creme.E003',
                           )
                     )

    return errors
