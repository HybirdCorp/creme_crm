# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from django.forms import DateTimeField, ModelChoiceField
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django.contrib.formtools.wizard import FormWizard

from creme_core.forms import CremeModelForm
from creme_core.forms.widgets import DateTimeWidget

from recurrents.models import RecurrentGenerator
from recurrents.registry import recurrent_registry


class RecurrentGeneratorEditForm(CremeModelForm):
    first_generation = DateTimeField(label=_(u'Date de la première récurrence'),
                                     required=True, widget=DateTimeWidget())

    class Meta:
        model = RecurrentGenerator
        exclude = CremeModelForm.exclude + ('last_generation', 'ct', 'template', 'is_working')


class RecurrentGeneratorCreateForm(RecurrentGeneratorEditForm):
    ct = ModelChoiceField(queryset=recurrent_registry.get_all_templates(),
                          label=_(u'Liste des types de ressources utilisables en tant que modèle'))

    class Meta:
        model = RecurrentGenerator
        exclude = CremeModelForm.exclude + ('is_working', 'template', 'last_generation')

    def save(self):
        instance = super(RecurrentGeneratorCreateForm, self).save()
        instance.last_generation = instance.first_generation
        instance.save()


class RecurrentGeneratorWizard(FormWizard):
    def __init__(self):
        # The second form of the wizard is set to None because it will be determined at execution
        super(RecurrentGeneratorWizard, self).__init__([RecurrentGeneratorCreateForm, None])

    def done(self, request, form_list):
        # We save in db the generator with his linked ressource
        generator_form = self.get_form(0, request.POST) # form corresponding to generator metadata
        resource_form  = self.get_form(1, request.POST) # form corresponding to the clonable resource

        if resource_form.is_valid():
            resource_form.save()
            generator_form.instance.template = resource_form.instance

        if generator_form.is_valid():
            generator_form.save()

        return HttpResponseRedirect(resource_form.instance.get_absolute_url())

    def process_step(self, request, form, step):
        if step == 0 and form.is_valid():
            self.form_list[1] = recurrent_registry.get_form_of_template(form.cleaned_data['ct'])

    def parse_params(self, request, *args, **kwargs):
        current_step = self.determine_step(request, *args, **kwargs)

        if request.method == 'POST' and current_step == 0:
            form = self.get_form(current_step, request.POST)
            if form.is_valid():
                self.initial[current_step + 1] = {
                    'ct': form.cleaned_data['ct'].id,
                }

    def get_template(self, step):
        return 'recurrents/wizard_generator.html'
