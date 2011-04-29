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

from django.utils.translation import ugettext_lazy as _
from django.forms import ModelChoiceField, ValidationError
from django.contrib.contenttypes.models import ContentType

from creme_core.models import EntityFilter
from creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme_core.forms.fields import MultiCremeEntityField, CremeEntityField

from persons.models import Contact

from sms.models import MessagingList


class MessagingListForm(CremeEntityForm):
    class Meta:
        model = MessagingList
        fields = ('user', 'name')


class AddContactsForm(CremeForm):
    recipients = MultiCremeEntityField(label=_(u'Contacts'),
                                       required=False, model=Contact) # other filter (name + email)??

    blocks = FieldBlockManager(('general', _(u'Contacts recipients'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(AddContactsForm, self).__init__(*args, **kwargs)
        self.messaging_list = entity

    def save(self):
        contacts = self.messaging_list.contacts

        #TODO: check if email if ok ????
        for contact in self.cleaned_data['recipients']:
            contacts.add(contact)


class AddPersonsFromFilterForm(CremeForm): #private class ???
    filters = ModelChoiceField(label=_(u'Filters'), queryset=EntityFilter.objects.none(), empty_label=_(u'All'), required=False)

    person_model = None #Contact/Organisation

    def __init__(self, entity, *args, **kwargs):
        super(AddPersonsFromFilterForm, self).__init__(*args, **kwargs)
        self.messaging_list = entity

        ct = ContentType.objects.get_for_model(self.person_model)
        self.fields['filters'].queryset = EntityFilter.objects.filter(entity_type=ct)

    def get_persons_m2m(self):
        raise NotImplementedError

    def save(self):
        persons   = self.get_persons_m2m()
        efilter = self.cleaned_data['filters']
        new_persons = self.person_model.objects.all()

        if efilter:
            new_persons = efilter.filter(new_persons)

        #TODO: check if phone number is ok ????
        for person in new_persons:
            persons.add(person)


class AddContactsFromFilterForm(AddPersonsFromFilterForm):
    blocks = FieldBlockManager(('general', _(u'Contacts recipients'), '*'))

    person_model = Contact

    def get_persons_m2m(self):
        return self.messaging_list.contacts
