# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2021  Hybird
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

from django.contrib.auth.forms import AuthenticationForm
from django.forms.fields import BooleanField
from django.forms.widgets import Input
from django.utils.translation import pgettext_lazy

from creme.persons.forms import quick

from .models import MobileFavorite


class MobileAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: factorise
        errors = self.errors

        for fname, field in self.fields.items():
            attrs = field.widget.attrs
            attrs['class'] = 'form-input' if fname not in errors else \
                             'form-input form-input-invalid'

            if field.required:
                attrs['required'] = ''


class PhoneInput(Input):
    input_type = 'tel'


class MobilePersonCreationFormMixin:
    def __init__(self):
        self.instance.user = self.user

        # NB: used by template (add_contact.html/add_orga.html)
        errors = self.errors

        for fname, field in self.fields.items():
            if fname != 'is_favorite':
                attrs = field.widget.attrs
                attrs['class'] = 'form-input' if fname not in errors else \
                                 'form-input form-input-invalid'

                if field.required:
                    attrs['required'] = ''

        self.custom_field_names = [
            self._build_customfield_name(cfield)
            for cfield, cvalue in self._customs
        ]


class MobileContactCreateForm(MobilePersonCreationFormMixin,
                              quick.ContactQuickForm):
    is_favorite = BooleanField(
        label=pgettext_lazy('mobile-contact', 'Is favorite'), required=False,
    )

    class Meta(quick.ContactQuickForm.Meta):
        fields = ('last_name', 'first_name', 'phone', 'mobile', 'email')
        widgets = {
            'phone':  PhoneInput,
            'mobile': PhoneInput,
        }

    def __init__(self, *args, **kwargs):
        quick.ContactQuickForm.__init__(self, *args, **kwargs)
        MobilePersonCreationFormMixin.__init__(self)

    def clean(self):
        self.cleaned_data['user'] = self.user  # NB: used in super().clean()
        return super().clean()

    def save(self, *args, **kwargs):
        contact = super().save(*args, **kwargs)

        if self.cleaned_data['is_favorite']:
            MobileFavorite.objects.create(entity=contact, user=self.user)

        return contact


class MobileOrganisationCreateForm(MobilePersonCreationFormMixin,
                                   quick.OrganisationQuickForm):
    is_favorite = BooleanField(label=pgettext_lazy('mobile-orga', 'Is favorite'), required=False)

    class Meta(quick.OrganisationQuickForm.Meta):
        fields = ('name', 'phone')

    def __init__(self, *args, **kwargs):
        quick.OrganisationQuickForm.__init__(self, *args, **kwargs)
        MobilePersonCreationFormMixin.__init__(self)

    def save(self, *args, **kwargs):
        orga = super().save(*args, **kwargs)

        if self.cleaned_data['is_favorite']:
            MobileFavorite.objects.create(entity=orga, user=self.user)

        return orga
