# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.conf import settings
from django.utils.timezone import now

from creme import __version__

from .gui.bricks import BricksManager
from .models import FieldsConfig


def get_logo_url(request):
    return {'logo_url': settings.LOGO_URL}


def get_css_theme(request):
    # NB: AnonymousUser has no 'theme_info' attribute (we need it for the login view)
    theme_info = getattr(request.user, 'theme_info', settings.THEMES[0])

    return {
        'THEME_NAME':         theme_info[0],
        'DEFAULT_THEME':      settings.THEMES[0][0],  # TODO: seems not used...
        'THEME_VERBOSE_NAME': theme_info[1],
    }


def get_today(request):
    return {'today': now()}


def get_blocks_manager(request):
    warnings.warn('"creme.creme_core.context_processor.get_blocks_manager" is deprecated ; '
                  'use "creme.creme_core.context_processor.get_bricks_manager" in your settings instead.',
                  DeprecationWarning
                 )
    return get_bricks_manager(request)


def get_bricks_manager(request):
    return {BricksManager.var_name: BricksManager()}


def get_fields_configs(request):
    return {'fields_configs': FieldsConfig.LocalCache()}


def get_shared_data(request):
    return {'shared': {}}


def get_version(request):
    return {'creme_version': __version__}


def get_hidden_value(request):
    return {'HIDDEN_VALUE': settings.HIDDEN_VALUE}


def get_django_version(request):
    if settings.DEBUG:
        from django import get_version
        return {'django_version': get_version()}
    return {}


def get_old_menu(request):
    return {'OLD_MENU': settings.OLD_MENU}


def get_site_domain(request):
    return {'SITE_DOMAIN': settings.SITE_DOMAIN}


def get_repository(request):
    return {'REPOSITORY': settings.REPOSITORY}
