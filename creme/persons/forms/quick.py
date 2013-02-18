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

from django.forms.fields import CharField
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeModelWithUserForm
from creme_core.models import Relation

from persons.constants import REL_SUB_EMPLOYED_BY
from persons.models import Contact, Organisation


class ContactQuickForm(CremeModelWithUserForm): #not CremeEntityForm to ignore custom fields
    organisation = CharField(label=_(u"Organisation"), required=False,
                             help_text=_(u'If no organisation is found, a new one will be created.')
                            )

    class Meta:
        model = Contact
        fields = ('user', 'last_name', 'first_name', 'phone', 'email')

    def save(self):
        contact = super(ContactQuickForm, self).save()

        orga_name = self.cleaned_data['organisation']
        if orga_name:
            orga = Organisation.objects.get_or_create(name=orga_name,
                                                      defaults={'user': contact.user}
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
