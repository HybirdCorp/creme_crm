# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.core.exceptions import ValidationError
from django.forms.fields import CharField
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms import CremeModelWithUserForm
from creme.creme_core.forms.validators import validate_linkable_model
from creme.creme_core.forms.widgets import Label
from creme.creme_core.models import Relation

from ..constants import REL_SUB_EMPLOYED_BY
from ..models import Contact, Organisation


class ContactQuickForm(CremeModelWithUserForm): #not CremeEntityForm to ignore custom fields
    organisation = CharField(label=_(u"Organisation"), required=False,
                             help_text=_(u'If no organisation is found, a new one will be created.'),
                            )

    class Meta:
        model = Contact
        fields = ('user', 'last_name', 'first_name', 'phone', 'email')

    def __init__(self, *args, **kwargs):
        super(ContactQuickForm, self).__init__(*args, **kwargs)

        has_perm = self.user.has_perm_to_link
        c_link_perm = has_perm(Contact, owner=None)
        o_link_perm = has_perm(Organisation, owner=None)

        self.has_perm_to_link = link_perm = (c_link_perm and o_link_perm)

        if not link_perm:
            orga_field = self.fields['organisation']
            orga_field.widget = Label()
            orga_field.help_text = ''
            orga_field.initial = ugettext(u'You are not allowed to link with a Contact') if not c_link_perm else \
                                 ugettext(u'You are not allowed to link with an Organisation')
        elif not self.can_create():
            self.fields['organisation'].help_text = ugettext(u'Enter the name of an existing Organisation.')

    def can_create(self):
        return self.user.has_perm_to_create(Organisation)

    def clean_organisation(self):
        orga_name = self.cleaned_data['organisation']

        if self.has_perm_to_link:
            if orga_name:
                orgas = self._get_organisations(orga_name)

                if not orgas:
                    if not self.can_create():
                        raise ValidationError(ugettext(u'You are not allowed to create an Organisation.'))

                    orga = None
                else:
                    has_perm = self.user.has_perm_to_link
                    #NB: remember that deleted Organisations are not linkable
                    linkable_orgas = [o for o in orgas if has_perm(o)]

                    if not linkable_orgas:
                        raise ValidationError(ugettext(u'No linkable Organisation found.'))

                    if len(linkable_orgas) > 1:
                        raise ValidationError(ugettext(u'Several Organisations with this name have been found.'))

                    orga = linkable_orgas[0]

                self.retrieved_orga = orga

        return orga_name

    def clean(self):
        cdata = self.cleaned_data

        if not self._errors and cdata['organisation']:
            owner = cdata['user']

            validate_linkable_model(Contact, self.user, owner)

            if self.has_perm_to_link and not self.retrieved_orga:
                validate_linkable_model(Organisation, self.user, owner)

        return cdata

    def _get_organisations(self, orga_name):
        return EntityCredentials.filter(self.user, Organisation.objects.filter(name=orga_name))

    def save(self):
        contact = super(ContactQuickForm, self).save()

        if self.has_perm_to_link:
            orga_name = self.cleaned_data['organisation']

            if orga_name:
                orga = self.retrieved_orga

                if orga is None:
                    #NB: we retry to get, because in an Formset, another Form can create the orga in its save()
                    orga = self._get_organisations(orga_name) \
                               .get_or_create(name=orga_name,
                                              defaults={'user': contact.user},
                                             )[0]

                Relation.objects.create(subject_entity=contact,
                                        type_id=REL_SUB_EMPLOYED_BY,
                                        object_entity=orga,
                                        user=contact.user,
                                       )

        return contact


class OrganisationQuickForm(CremeModelWithUserForm):
    class Meta:
        model = Organisation
        fields = ('name', 'user')
