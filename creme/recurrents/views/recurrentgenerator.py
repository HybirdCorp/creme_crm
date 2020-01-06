# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from creme.creme_core.views import generic

from .. import get_rgenerator_model
from ..constants import DEFAULT_HFILTER_RGENERATOR
from ..forms import recurrentgenerator as generator_forms

RecurrentGenerator = get_rgenerator_model()


class RecurrentGeneratorWizard(generic.EntityCreationWizard):
    # NB: in deed, the second form is just a place holder ;
    #     it will be dynamically replaced by a form from 'recurrent_registry' (see get_form().
    form_list = [generator_forms.RecurrentGeneratorCreateForm] * 2
    model = RecurrentGenerator

    def done_save(self, form_list):
        generator_form, resource_form = form_list
        generator_form.instance.template = resource_form.save()
        generator_form.save()

    def get_form(self, step=None, data=None, files=None):
        from ..registry import recurrent_registry

        form = None

        # Step can be None (see WizardView doc)
        if step is None:
            step = self.steps.current

        if step == '1':
            prev_data = self.get_cleaned_data_for_step('0')

            ctype = prev_data['ct']
            form_class = recurrent_registry.get_form_of_template(ctype)

            kwargs = self.get_form_kwargs(step)
            kwargs.update(data=data,
                          files=files,
                          prefix=self.get_form_prefix(step, None),
                          initial=self.get_form_initial(step),  # Not really useful here...
                          ct=ctype,
                         )
            form = form_class(**kwargs)
        else:
            form = super().get_form(step, data, files)

        return form


class RecurrentGeneratorDetail(generic.EntityDetail):
    model = RecurrentGenerator
    template_name = 'recurrents/view_generator.html'
    pk_url_kwarg = 'generator_id'


class RecurrentGeneratorEdition(generic.EntityEdition):
    model = RecurrentGenerator
    form_class = generator_forms.RecurrentGeneratorEditForm
    pk_url_kwarg = 'generator_id'


class RecurrentGeneratorsList(generic.EntitiesList):
    model = RecurrentGenerator
    default_headerfilter_id = DEFAULT_HFILTER_RGENERATOR
