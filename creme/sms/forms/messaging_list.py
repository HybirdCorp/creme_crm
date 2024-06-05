################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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
from django.forms import ModelChoiceField
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from creme.creme_core.forms import CremeForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField
from creme.creme_core.models import EntityFilter
from creme.persons import get_contact_model

Contact = get_contact_model()


class AddContactsForm(CremeForm):
    # TODO: other filter (name + email) ?
    recipients = MultiCreatorEntityField(
        label=_('Contacts'), required=False, model=Contact,
    )

    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Contact-recipients'), 'fields': '*',
    })

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        contacts = self.messaging_list.contacts

        # TODO: check if email is OK?
        for contact in self.cleaned_data['recipients']:
            contacts.add(contact)


class AddPersonsFromFilterForm(CremeForm):  # private class ???
    filters = ModelChoiceField(
        label=_('Filters'),
        queryset=EntityFilter.objects.none(),
        empty_label=pgettext_lazy('creme_core-filter', 'All'),
        required=False,
    )

    person_model = None  # Contact/Organisation

    def __init__(self, entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messaging_list = entity

        ct = ContentType.objects.get_for_model(self.person_model)
        self.fields['filters'].queryset = EntityFilter.objects\
                                                      .filter_by_user(self.user)\
                                                      .filter(entity_type=ct)

    def get_persons_m2m(self):
        raise NotImplementedError

    def save(self):
        persons = self.get_persons_m2m()
        efilter = self.cleaned_data['filters']
        new_persons = self.person_model.objects.filter(is_deleted=False)

        if efilter:
            new_persons = efilter.filter(new_persons)

        # TODO: check if phone number is ok ????
        for person in new_persons:
            persons.add(person)


class AddContactsFromFilterForm(AddPersonsFromFilterForm):
    blocks = FieldBlockManager({
        'id': 'general', 'label': _('Contact-recipients'), 'fields': '*',
    })

    person_model = Contact

    def get_persons_m2m(self):
        return self.messaging_list.contacts
