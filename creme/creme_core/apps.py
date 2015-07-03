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

from imp import find_module
import logging
from sys import argv

from django.apps import AppConfig, apps
from django.core import checks
from django.utils.translation import ugettext_lazy as _

from .checks import Tags


logger = logging.getLogger(__name__)


class CremeAppConfig(AppConfig):
    dependencies = () # Overload ; eg: ['creme.persons']

    def ready(self):
        # NB: it seems we cannot transform this a check_deps(self, **kwargs) method
        # because we get an error from django [AttributeError: 'instancemethod' object has no attribute 'tags']
        def check_deps(**kwargs):
            return [checks.Error("depends on the app '%s' which is not installed." % dep,
                                 hint='Check the INSTALLED_CREME_APPS setting in your'
                                      ' local_settings.py/project_settings.py',
                                 obj=self.name,
                                 id='creme.E001',
                                )
                        for dep in self.dependencies
                            if not apps.is_installed(dep)
                   ]

        checks.register(Tags.settings)(check_deps)


class CremeCoreConfig(CremeAppConfig):
    name = 'creme.creme_core'
    verbose_name = _(u'Core')

    def ready(self):
        super(CremeCoreConfig, self).ready()

        if 'migrate' in argv: # problem with ContentType table which can be not created yet.
            return

        # We check the badly uninstalled apps
        # NB: not a "django because it is for final users
        for app_label in apps.get_model('contenttypes.ContentType') \
                             .objects \
                             .order_by('app_label') \
                             .distinct() \
                             .values_list('app_label', flat=True):
            try:
                apps.get_app_config(app_label)
            except LookupError:
                logger.warning("""The app "%s" seems not been correctly uninstalled. """
                               """If it's a Creme app, uninstall it with the command "creme_uninstall" """
                               """(you must enable this app in your settings before).""" % app_label
                              )

        #ForeignKey's formfield() hooking --------------------------------------
        #TODO: move to creme_config ??

        from django.db.models import ForeignKey

        from creme.creme_config.forms.fields import CreatorModelChoiceField

        original_fk_formfield = ForeignKey.formfield

        def new_fk_formfield(self, **kwargs):
            defaults = {'form_class': CreatorModelChoiceField}
            defaults.update(kwargs)

            return original_fk_formfield(self, **defaults)

        ForeignKey.formfield = new_fk_formfield

        # ----------------------------------------------------------------------
        # we load the 'creme_core_register.py' module of each app
        #TODO: use creme_core.utils.imports ???
        for app_config in apps.get_app_configs():
            app_name = app_config.name

            try:
                #find_module("creme_core_register", __import__(app_name, {}, {}, [app_name.split(".")[-1]]).__path__)
                find_module("creme_core_register", __import__(app_name, {}, {}, [app_config.label]).__path__)
            except ImportError:
                # there is no creme_core_register.py, skip it
                continue

            __import__("%s.creme_core_register" % app_name)

