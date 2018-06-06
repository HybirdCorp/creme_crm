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


# Model Fields Hooking ---------------------------------------------------------
from creme.creme_core.core.field_tags import _add_tags_to_fields

_add_tags_to_fields()


# ForeignKey's null_label adding ------------------------------------------------
from django.db.models import ForeignKey


def _get_null_label(self):
    return getattr(self, '_creme_null_label', '')


def _set_null_label(self, null_label):
    self._creme_null_label = null_label

    return self

ForeignKey.get_null_label = _get_null_label
ForeignKey.set_null_label = _set_null_label


# ------------------------------------------------------------------------------


def get_concrete_model(model_setting):
    """Returns the concrete model that is active in this project corresponding
    to the setting value.
    @param model_setting A string corresponding to an entry of setting.py,
           which contains a value in the form ''app_label.model_name'.
    @return A model class.
    """
    from django.apps import apps
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured

    model_str = getattr(settings, model_setting)

    try:
        return apps.get_model(model_str)
    except ValueError:
        raise ImproperlyConfigured("{} must be of the form 'app_label.model_name'".format(model_setting))
    except LookupError:
        raise ImproperlyConfigured("{} refers to model '{}' that has not been installed".format(
                                            model_setting, model_str,
                                        )
                                  )


# ------------------------------------------------------------------------------

default_app_config = 'creme.creme_core.apps.CremeCoreConfig'
