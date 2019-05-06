# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2019  Hybird
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

from creme.creme_core.forms import CremeModelForm

from creme.persons import get_organisation_model
from creme.persons.forms.quick import ContactQuickForm

from .models import MobileFavorite


Organisation = get_organisation_model()


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


class MobileContactCreateForm(ContactQuickForm):
    is_favorite = BooleanField(label=pgettext_lazy('mobile-contact', 'Is favorite'), required=False)

    class Meta(ContactQuickForm.Meta):
        fields = ('last_name', 'first_name', 'phone', 'mobile', 'email')
        widgets = {
            'phone':  PhoneInput,
            'mobile': PhoneInput,
          }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = self.user
        # del self.fields['user']

        errors = self.errors

        for fname, field in self.fields.items():
            if fname != 'is_favorite':
                attrs = field.widget.attrs
                attrs['class'] = 'form-input' if fname not in errors else \
                                 'form-input form-input-invalid'

                if field.required:
                    attrs['required'] = ''

    def clean(self):
        self.cleaned_data['user'] = self.user  # NB: used in super().clean()
        return super().clean()

    def save(self, *args, **kwargs):
        contact = super().save(*args, **kwargs)

        if self.cleaned_data['is_favorite']:
            MobileFavorite.objects.create(entity=contact, user=self.user)

        return contact


class MobileOrganisationCreateForm(CremeModelForm):
    is_favorite = BooleanField(label=pgettext_lazy('mobile-orga', 'Is favorite'), required=False)

    class Meta:
        model = Organisation
        fields = ('name', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = self.user

        # TODO: factorise
        errors = self.errors

        for fname, field in self.fields.items():
            if fname != 'is_favorite':
                attrs = field.widget.attrs
                attrs['class'] = 'form-input' if fname not in errors else \
                                 'form-input form-input-invalid'

                if field.required:
                    attrs['required'] = ''

    def save(self, *args, **kwargs):
        orga = super().save(*args, **kwargs)

        if self.cleaned_data['is_favorite']:
            MobileFavorite.objects.create(entity=orga, user=self.user)

        return orga
