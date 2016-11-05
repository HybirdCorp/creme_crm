# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
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
from django.forms import ModelChoiceField, ValidationError
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeEntityForm, CremeForm, FieldBlockManager
from creme.creme_core.forms.fields import MultiCreatorEntityField, CreatorEntityField
from creme.creme_core.models import EntityFilter

from creme.persons import get_contact_model, get_organisation_model

from .. import get_mailinglist_model


MailingList   = get_mailinglist_model()
Contact       = get_contact_model()
Organisation  = get_organisation_model()


class MailingListForm(CremeEntityForm):
    class Meta:
        model  = MailingList
        fields = ('user', 'name')


class AddContactsForm(CremeForm):
    recipients = MultiCreatorEntityField(label=_(u'Contacts'), required=False, model=Contact)  # other filter (name + email)??

    blocks = FieldBlockManager(('general', _(u'Contacts recipients'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(AddContactsForm, self).__init__(*args, **kwargs)
        self.ml = entity

    def save(self):
        contacts = self.ml.contacts

        # TODO: check if email if ok ????
        for contact in self.cleaned_data['recipients']:
            contacts.add(contact)


class AddOrganisationsForm(CremeForm):  # TODO: factorise
    recipients = MultiCreatorEntityField(label=_(u'Organisations'), required=False, model=Organisation) # other filter (name + email)??

    blocks = FieldBlockManager(('general', _(u'Organisations recipients'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(AddOrganisationsForm, self).__init__(*args, **kwargs)
        self.ml = entity

    def save(self):
        organisations = self.ml.organisations

        #TODO: check if email if ok ????
        for organisation in self.cleaned_data['recipients']:
            organisations.add(organisation)


class _AddPersonsFromFilterForm(CremeForm):
    filters = ModelChoiceField(label=_(u'Filters'), queryset=EntityFilter.objects.none(),
                               empty_label=_(u'All'), required=False,
                              )

    person_model = None  # Contact/Organisation

    def __init__(self, entity, *args, **kwargs):
        super(_AddPersonsFromFilterForm, self).__init__(*args, **kwargs)
        self.ml = entity

        ct = ContentType.objects.get_for_model(self.person_model)
        self.fields['filters'].queryset = EntityFilter.get_for_user(self.user, ct)

    def get_persons_m2m(self):
        raise NotImplementedError

    def save(self):
        persons = self.get_persons_m2m()
        efilter = self.cleaned_data['filters']
        new_persons = self.person_model.objects.filter(is_deleted=False)

        if efilter:
            new_persons = efilter.filter(new_persons)

        # TODO: check if email if ok ????
        for person in new_persons:
            persons.add(person)


class AddContactsFromFilterForm(_AddPersonsFromFilterForm):
    blocks = FieldBlockManager(('general', _(u'Contacts recipients'), '*'))

    person_model = Contact

    def get_persons_m2m(self):
        return self.ml.contacts


class AddOrganisationsFromFilterForm(_AddPersonsFromFilterForm):
    blocks = FieldBlockManager(('general', _(u'Organisations recipients'), '*'))

    person_model = Organisation

    def get_persons_m2m(self):
        return self.ml.organisations


class AddChildForm(CremeForm):
    child = CreatorEntityField(label=_(u'List'), required=True, model=MailingList)

    error_messages = {
        'own_child': _(u"A list can't be its own child"),
        'in_parents': _(u'List already in the parents'),
        'in_children': _(u'List already in the children'),
    }

    blocks = FieldBlockManager(('general', _(u'Child mailing list'), '*'))

    def __init__(self, entity, *args, **kwargs):
        super(AddChildForm, self).__init__(*args, **kwargs)
        self.ml = entity

    def clean_child(self):
        child = self.cleaned_data['child']
        ml    = self.ml

        if ml.id == child.id:
            raise ValidationError(self.error_messages['own_child'], code='own_child')

        if ml.already_in_parents(child.id):
            raise ValidationError(self.error_messages['in_parents'], code='in_parents')

        if ml.already_in_children(child.id):
            raise ValidationError(self.error_messages['in_children'], code='in_children')

        return child

    def save(self):
        self.ml.children.add(self.cleaned_data['child'])
