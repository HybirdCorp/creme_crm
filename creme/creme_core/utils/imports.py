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

import logging
from importlib import import_module

from django.apps import apps

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


def import_object(objectpath):
    i = objectpath.rfind('.')
    module, attr = objectpath[:i], objectpath[i + 1:]
    try:
        mod = import_module(module)
    except ImportError:
        raise

    try:
        result = getattr(mod, attr)
    except AttributeError as e:
        raise AttributeError(
            f'Module "{module}" does not define a "{attr}" object'
        ) from e

    return result


def safe_import_object(objectpath):
    try:
        return import_object(objectpath)
    except Exception as e:
        logger.warning('An error occurred trying to import "%s": [%s]', objectpath, e)
