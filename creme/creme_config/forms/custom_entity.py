################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024-2025  Hybird
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

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.models import CustomEntityType, HeaderFilter


class CustomEntityTypeCreationForm(CremeForm):
    error_messages = {
        'unique_name': _('There is already a type with this name.')
    }

    name        = forms.CharField(label=_('Name'), max_length=50)
    plural_name = forms.CharField(label=_('Name (plural)'), max_length=50)

    def clean_name(self):
        name = self.cleaned_data['name']

        if CustomEntityType.objects.filter(name=name, enabled=True).exists():
            raise ValidationError(
                self.error_messages['unique_name'], code='unique_name',
            )

        return name

    # TODO: @atomic?
    def save(self, *args, **kwargs):
        cdata = self.cleaned_data

        instances = [
            *CustomEntityType.objects.filter(enabled=False)
                                     .order_by('id')
                                     .select_for_update(),
        ]
        instance = instances[0]  # TODO: manage error?
        instance.enabled = True
        instance.name        = cdata['name']
        instance.plural_name = cdata['plural_name']
        instance.save()

        HeaderFilter.objects.proxy(
            id=f'creme_core-hf_custom_entity_{instance.id}',
            name=gettext('{model} view').format(model=instance.name),
            model=instance.entity_model,
            # is_custom=False,
            cells=[(EntityCellRegularField, 'name')],
        ).get_or_create()

        return instance


class CustomEntityTypeEditionForm(CremeModelForm):
    error_messages = {
        'unique_name': _('There is already a type with this name.')
    }

    class Meta(CremeModelForm.Meta):
        model = CustomEntityType

    def clean_name(self):
        name = self.cleaned_data['name']

        if CustomEntityType.objects.filter(name=name, enabled=True).exists():
            raise ValidationError(
                self.error_messages['unique_name'], code='unique_name',
            )

        return name
