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

from django.utils.translation import ugettext as _
from django.forms.util import ValidationError

from creme_core.forms import CremeModelForm, CremeEntityField

from persons.models.organisation import Organisation, Address


class AddressWithOrganisationForm(CremeModelForm):
    organisation = CremeEntityField(required=True, model=Organisation)

    class Meta:
        model = Address
        exclude = ('content_type', 'object_id')

    def __init__(self, *args, **kwargs):
        super(AddressWithOrganisationForm, self).__init__(*args, **kwargs)
        self.fields['organisation'].initial = self.initial['organisation_id']

    def save(self):
        cleaned_data = self.cleaned_data
        instance     = self.instance
        instance.content_type = cleaned_data['organisation'].entity_type
        instance.object_id    = cleaned_data['organisation'].id
        super(AddressWithOrganisationForm, self).save()


def clean_address(address_id):
    try:
        address = Address.objects.get(pk=address_id)
    except Address.DoesNotExist:
        raise ValidationError(_(u"This address doesn't exist or doesn't exist any more"))
    return address
