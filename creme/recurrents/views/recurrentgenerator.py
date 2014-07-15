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

from django.contrib.formtools.wizard.views import SessionWizardView
from django.db.transaction import commit_on_success
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.views.generic import view_entity, list_view, edit_entity

from ..forms.recurrentgenerator import RecurrentGeneratorEditForm #RecurrentGeneratorWizard
from ..models import RecurrentGenerator
from ..registry import recurrent_registry

#_wizard = RecurrentGeneratorWizard()

#@login_required
#@permission_required('recurrents')
#@permission_required('recurrents.add_recurrentgenerator')
#def add(request):
    #return _wizard(request)

#TODO: creds
class RecurrentGeneratorWizard(SessionWizardView):
    template_name = 'creme_core/generics/blockform/add_wizard.html'

    @method_decorator(login_required)
    @method_decorator(permission_required('recurrents'))
    @method_decorator(permission_required('recurrents.add_recurrentgenerator'))
    def dispatch(self, *args, **kwargs):
        return super(RecurrentGeneratorWizard, self).dispatch(*args, **kwargs)

    def done(self, form_list, **kwargs):
        generator_form = form_list[0]
        resource_form  = form_list[1]

        with commit_on_success():
            generator_form.instance.template = resource_form.save()
            generator_form.save()

        return redirect(resource_form.instance)

    def get_context_data(self, form, **kwargs):
        context = super(RecurrentGeneratorWizard, self).get_context_data(form=form, **kwargs)
        context['title'] = RecurrentGenerator.creation_label
        context['submit_label'] = _('Save the generator')

        return context

    def get_form(self, step=None, data=None, files=None):
        form = None

        # step can be None (see WizardView doc)
        if step is None:
            step = self.steps.current

        if step == '1':
            #prev_data = self.get_cleaned_data_for_step(self.get_prev_step(self.steps.current))
            prev_data =  self.get_cleaned_data_for_step('0')

            #if prev_data is not None:
            ctype = prev_data['ct']
            form_class = recurrent_registry.get_form_of_template(ctype)

            kwargs = self.get_form_kwargs(step)
            kwargs.update(data=data,
                          files=files,
                          prefix=self.get_form_prefix(step, None),
                          initial=self.get_form_initial(step), #not really useful here...
                          ct=ctype,
                         )
            form = form_class(**kwargs)

        #if form is None:
        else:
            form = super(RecurrentGeneratorWizard, self).get_form(step, data, files)

        return form

    def get_form_kwargs(self, step):
        return {'user': self.request.user}


@login_required
@permission_required('recurrents')
def edit(request, generator_id):
    return edit_entity(request, generator_id, RecurrentGenerator, RecurrentGeneratorEditForm)

@login_required
@permission_required('recurrents')
def listview(request):
    return list_view(request, RecurrentGenerator, extra_dict={'add_url': '/recurrents/generator/add'})

@login_required
@permission_required('recurrents')
def detailview(request, generator_id):
    return view_entity(request, generator_id, RecurrentGenerator,
                       '/recurrents/generator', 'recurrents/view_generator.html',
                      )
