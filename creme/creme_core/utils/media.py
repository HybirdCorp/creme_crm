# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from mediagenerator.utils import media_url

from ..global_info import get_global_info


def get_creme_media_url(theme: str, url: str) -> str:
    return media_url(f'{theme}/{url}')


def creme_media_themed_url(url: str) -> str:
    return get_creme_media_url(get_current_theme(), url)


def get_current_theme() -> str:
    theme_info = getattr(get_global_info('user'), 'theme_info', None) or settings.THEMES[0]

    return theme_info[0]


def get_current_theme_from_context(context) -> str:
    try:
        return context['THEME_NAME']
    except KeyError:
        return get_current_theme()
