################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
from creme.creme_core import get_world_settings_model

from .gui.bricks import BrickManager
from .models import FieldsConfig


def get_base_template(request):
    return {
        'BASE_HTML': settings.BASE_HTML,
        'BASE_HTML_EXTRA_INCLUDED': settings.BASE_HTML_EXTRA_INCLUDED,
    }


def get_software_label(request):
    return {'SOFTWARE_LABEL': settings.SOFTWARE_LABEL}


def get_css_theme(request):
    # NB: AnonymousUser has no 'theme_info' attribute (we need it for the login view)
    theme_info = getattr(request.user, 'theme_info', settings.THEMES[0])

    return {
        'THEME_NAME':         theme_info[0],
        'THEME_VERBOSE_NAME': theme_info[1],
    }


def get_today(request):
    return {'today': now()}


# TODO: rename "get_brick_manager"
def get_bricks_manager(request):
    return {BrickManager.var_name: BrickManager()}


def get_fields_configs(request):
    return {'fields_configs': FieldsConfig.LocalCache()}


def get_shared_data(request):
    return {'shared': {}}


def get_version(request):
    return {'creme_version': __version__}


def get_hidden_value(request):
    return {'HIDDEN_VALUE': settings.HIDDEN_VALUE}


def get_jqmigrate_mute(request):
    return {
        'JQUERY_MIGRATE_MUTE': getattr(settings, 'JQUERY_MIGRATE_MUTE', False)
    }


def get_django_version(request):
    if settings.DEBUG:
        from django import get_version
        return {'django_version': get_version()}
    return {}


def get_site_domain(request):
    return {'SITE_DOMAIN': settings.SITE_DOMAIN}


def get_repository(request):
    return {'REPOSITORY': settings.REPOSITORY}


def get_world_settings(request):
    return {'world_settings': get_world_settings_model().objects.instance()}


def get_entities_deletion_allowed(request):
    warnings.warn(
        'The context processor "get_entities_deletion_allowed" is deprecated;'
        'you should probably use {% get_deletion_info ... %} instead.',
        DeprecationWarning,
    )

    return {'ENTITIES_DELETION_ALLOWED': settings.ENTITIES_DELETION_ALLOWED}
