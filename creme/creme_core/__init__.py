# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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

#from imp import find_module
#import logging
import warnings

#from django.conf import settings

from creme.creme_core.core.field_tags import _add_tags_to_fields


#logger = logging.getLogger(__name__)


#todo: move to core ?
#todo: use creme_core.utils.imports ???
def autodiscover():
    """Auto-discover in INSTALLED_APPS the creme_core_register.py files. DEPRECATED"""
#    for app in settings.INSTALLED_APPS: #todo: only INSTALLED_CREME_APPS
#        try:
#            find_module("creme_core_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
#        except ImportError:
#            # there is no app creme_config.py, skip it
#            continue
#        __import__("%s.creme_core_register" % app)
    warnings.warn("creme_core.autodiscover() function is deprecated.",
                  DeprecationWarning
                 )

_add_tags_to_fields()


#ForeignKey's null_label adding ------------------------------------------------
from django.db.models import ForeignKey

def _get_null_label(self):
    return getattr(self, '_creme_null_label', '')

def _set_null_label(self, null_label):
    self._creme_null_label = null_label

    return self

ForeignKey.get_null_label = _get_null_label
ForeignKey.set_null_label = _set_null_label

# ------------------------------------------------------------------------------

default_app_config = 'creme.creme_core.apps.CremeCoreConfig'
