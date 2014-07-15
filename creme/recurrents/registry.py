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

from django.contrib.contenttypes.models import ContentType

# TODO : AppRecurrentRegistry indirection useless (at least for now)

class TemplateRecurrentRegistry:
    def __init__(self, model, template_model, template_form):
        self.model          = model
        self.template_model = template_model
        self.template_form  = template_form


class AppRecurrentRegistry:
    def __init__(self, app_name):
        self.app_name = app_name
        self._templates = []

    def add(self, model, template_model, template_form):
        self._templates.append(TemplateRecurrentRegistry(model, template_model, template_form))

    def __iter__(self):
        return iter(self._templates)


class RecurrentRegistry:
    def __init__(self):
        self._apps = {}

    def register(self, *to_register):
        app_registries = self._apps

        for model, template_model, template_form in to_register:
            app_name = model._meta.app_label
            app_registry = app_registries.get(app_name)

            if app_registry is None:
                app_registry = app_registries[app_name] = AppRecurrentRegistry(app_name)

            app_registry.add(model, template_model, template_form)

    #Removed for version 1.5 (7 July 2014)
    #def get_all_templates(self):
        #get_ct = ContentType.objects.get_for_model
        #ct_pks = [get_ct(template_entry.model).id for app_registry in self._apps.itervalues() for template_entry in app_registry]

        #return ContentType.objects.filter(pk__in=ct_pks)

    @property
    def ctypes(self):
        get_ct = ContentType.objects.get_for_model

        for app_registry in self._apps.itervalues():
            for template_entry in app_registry:
                yield get_ct(template_entry.model)

    def get_form_of_template(self, ct_template):
        for app_registry in self._apps.itervalues():
            for template_entry in app_registry:
                if template_entry.model == ct_template.model_class():
                    return template_entry.template_form


recurrent_registry = RecurrentRegistry()
