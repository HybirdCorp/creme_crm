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

from django.forms import ModelChoiceField
from django.utils.translation import gettext as _

from creme import persons
from creme.creme_core.forms.mass_import import (
    EntityExtractorField,
    ImportForm4CremeEntity,
)

Organisation = persons.get_organisation_model()
Contact = persons.get_contact_model()


def get_mass_form_builder(header_dict, choices):
    class OpportunityMassImportForm(ImportForm4CremeEntity):
        target = EntityExtractorField(
            models_info=[
                (Organisation, 'name'),
                (Contact, 'last_name'),
            ],
            choices=choices, label=_('Target'),
        )
        emitter = ModelChoiceField(
            label=_('Concerned organisation'),
            empty_label=None,
            queryset=Organisation.objects.filter_managed_by_creme(),
        )

        def _pre_instance_save(self, instance, line):
            cdata = self.cleaned_data

            if not instance.pk:  # Creation
                instance.emitter = cdata['emitter']

            target, err_msg = cdata['target'].extract_value(line, self.user)
            instance.target = target
            self.append_error(err_msg)  # Error is really appended if 'err_msg' is not empty

    return OpportunityMassImportForm
