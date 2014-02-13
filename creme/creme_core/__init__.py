# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from imp import find_module
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.utils import DatabaseError

from creme.creme_core.core.field_tags import _add_tags_to_fields


logger = logging.getLogger(__name__)


#TODO: move to core ?
#TODO: use creme_core.utils.imports ???
def autodiscover():
    """Auto-discover in INSTALLED_APPS the creme_core_register.py files."""
    for app in settings.INSTALLED_APPS:
        try:
            find_module("creme_core_register", __import__(app, {}, {}, [app.split(".")[-1]]).__path__)
        except ImportError:
            # there is no app creme_config.py, skip it
            continue
        __import__("%s.creme_core_register" % app)


_add_tags_to_fields()


#ForeignKey's formfield() hooking --------------------------------------------
#TODO: move to creme_config ??
from django.db.models import ForeignKey

original_fk_formfield = ForeignKey.formfield

def new_fk_formfield(self, **kwargs):
    from creme.creme_config.forms.fields import CreatorModelChoiceField

    defaults = {'form_class': CreatorModelChoiceField}
    defaults.update(kwargs)

    return original_fk_formfield(self, **defaults)

ForeignKey.formfield = new_fk_formfield

#-----------------------------------------------------------------------------
from django.db.transaction import commit_on_success

try:
    with commit_on_success():
        app_labels = list(ContentType.objects.order_by('app_label')
                                                .distinct()
                                                .values_list('app_label', flat=True)
                            )
except DatabaseError: #happens during syncdb (ContentType table does not exist yet)
    pass
else:
    _INSTALLED_APPS = frozenset(app_name.split('.')[-1] for app_name in settings.INSTALLED_APPS)

    for app_label in app_labels:
        if app_label not in _INSTALLED_APPS:
            logger.warning("""The app "%s" seems not been correctly uninstalled. """
                        """If it's a Creme app, uninstall it with the command "creme_uninstall" """
                        """(you must enable this app in your settings before).""" % app_label
                        )

    del _INSTALLED_APPS
