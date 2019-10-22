# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2019  Hybird
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

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.forms import fields
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm  # CremeForm
from creme.creme_core.forms.fields import CTypeChoiceField
from creme.creme_core.forms.widgets import DynamicSelect, Label
from creme.creme_core.models import CremeEntity, FieldsConfig


# class FieldsConfigAddForm(CremeForm):
class FieldsConfigAddForm(CremeModelForm):
    ctype = CTypeChoiceField(
        label=_('Related resource'),
        help_text=_('The proposed types of resource have at least a field which can be hidden.'),
        widget=DynamicSelect(attrs={'autocomplete': True}),
    )

    class Meta(CremeModelForm.Meta):
        model = FieldsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        models = [*filter(FieldsConfig.is_model_valid, apps.get_models())]
        # NB: we use <FieldsConfig.get_4_models()> to take advantage of its cache ;
        #     it useful because this constructor can be called several times in a request
        #     because of our wizard (which fill the instance by calling all
        #     previous steps' validation).
        # Old code:
        #  used_ct_ids = {*FieldsConfig.objects.values_list('content_type', flat=True)}
        excluded_ct_ids = {
            # Do not want a choice "creme entity" ('description' can be hidden).
            ContentType.objects.get_for_model(CremeEntity).id,

            # Exclude ContentType which already have a configuration
            *(fc.content_type_id
                for fc in FieldsConfig.get_4_models(models).values()
                    if not fc._state.adding  # <True> means the FieldsConfig is in DB
             )
        }
        self.ctypes = ctypes = [
            ct
                for ct in map(ContentType.objects.get_for_model, models)
                    if ct.id not in excluded_ct_ids
        ]

        if ctypes:
            self.fields['ctype'].ctypes = ctypes
        else:
            # TODO: remove the 'submit' button ?
            self.fields['ctype'] = fields.CharField(
                label=_('Related resource'),
                required=False, widget=Label,
                initial=_('All configurable types of resource are already configured.'),
            )

    def clean(self, *args, **kwargs):
        cdata = super().clean(*args, **kwargs)

        if not self._errors:
            instance = self.instance
            instance.content_type = self.cleaned_data['ctype']
            instance.descriptions = ()

        return cdata

    # def save(self):
    #     if self.ctypes:
    #         return FieldsConfig.objects.create(content_type=self.cleaned_data['ctype'],
    #                                            descriptions=(),
    #                                           )
    def save(self, *args, **kwargs):
        if self.ctypes:  # NB: remove if we raise a ValidationError in clean()
            super().save(*args, **kwargs)

        return self.instance


class FieldsConfigEditForm(CremeModelForm):
    hidden = fields.MultipleChoiceField(
        label=_('Hidden fields'), choices=(), required=False,
    )

    class Meta(CremeModelForm.Meta):
        model = FieldsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        hidden_f = self.fields['hidden']
        hidden_f.choices = FieldsConfig.field_enumerator(instance.content_type.model_class()).choices()

        if instance.pk:
            hidden_f.initial = [f.name for f in instance.hidden_fields]

    def clean(self, *args, **kwargs):
        cdata = super().clean(*args, **kwargs)

        if not self._errors:
            HIDDEN = FieldsConfig.HIDDEN
            self.instance.descriptions = [
                (field_name, {HIDDEN: True})
                    for field_name in self.cleaned_data['hidden']
            ]

        return cdata

    # def save(self, *args, **kwargs):
    #     HIDDEN = FieldsConfig.HIDDEN
    #     self.instance.descriptions = [
    #         (field_name, {HIDDEN: True})
    #             for field_name in self.cleaned_data['hidden']
    #     ]
    #     return super().save(*args, **kwargs)
