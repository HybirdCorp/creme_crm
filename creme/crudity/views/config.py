################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2022-2023  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm
from creme.creme_core.views import generic
from creme.crudity import models

from ..fetchers import CrudityFetcherManager
from ..forms import config as config_forms


class FetcherConfigItemCreationWizard(generic.CremeModelCreationWizardPopup):
    model = models.FetcherConfigItem

    # NB: in deed, the second form is just a place holder ;
    #     it will be dynamically replaced by a form BLABLABLA. TODO
    form_list = [
        config_forms.FetcherItemCreationStep,
        CremeForm,
    ]

    title = _('New fetcher configuration')
    submit_label = _('Save the configuration')
    permissions = 'crudity.can_admin'

    def done_save(self, form_list):
        item_form, options_form = form_list

        item = item_form.instance
        item.options = options_form.cleaned_data

        item.save()

    def get_form(self, step=None, data=None, files=None):
        form = None

        # Step can be None (see WizardView doc)
        if step is None:
            step = self.steps.current

        if step == '1':
            class_id = self.get_cleaned_data_for_step('0')['class_id']

            # TODO: method 'fetcher_class()' + unit test
            fetcher_cls = None
            for cls in CrudityFetcherManager().fetcher_classes:
                if cls.id == class_id:
                    fetcher_cls = cls
                    break
            else:
                raise ValueError('Invalid fetcher class')  # Should not happen after cleaning...

            kwargs = self.get_form_kwargs(step)
            kwargs.update(
                data=data,
                files=files,
                prefix=self.get_form_prefix(step, None),
                initial=self.get_form_initial(step),  # Not really useful here...
            )

            form = fetcher_cls.options_form(**kwargs)
        else:
            form = super().get_form(step, data, files)

        return form


class MachineConfigItemCreationWizard(generic.CremeModelCreationWizardPopup):
    model = models.MachineConfigItem
    form_list = [
        config_forms.MachineItemCreationStep,
        config_forms.ExtractorsStep,
    ]
    permissions = 'crudity.can_admin'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = self.model()

    def done_save(self, form_list):
        for form in form_list:
            form.save()

        self.item.save()

    def get_form_instance(self, step):
        # We fill the instance with the previous step
        # (so recursively all previous should be used)
        self.validate_previous_steps(step)

        return self.item
