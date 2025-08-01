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

import logging
from importlib import import_module

from django.apps import apps
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def import_apps_sub_modules(module_name):
    """Iterate on installed apps & for each one get a sub-module (if it exists).

    @param module_name: string.
    @return: a list of modules.
    """
    modules = []

    for app_config in apps.get_app_configs():
        try:
            mod = import_module(f'{app_config.name}.{module_name}')
        except ImportError:
            continue
        else:
            modules.append(mod)

    return modules


def safe_import_object(objectpath):
    try:
        return import_string(objectpath)
    except Exception as e:
        logger.warning('An error occurred trying to import "%s": [%s]', objectpath, e)
