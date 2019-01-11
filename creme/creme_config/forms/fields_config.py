# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
from django.forms.fields import MultipleChoiceField, CharField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.forms.fields import CTypeChoiceField
from creme.creme_core.forms.widgets import DynamicSelect, Label
from creme.creme_core.models import FieldsConfig


class FieldsConfigAddForm(CremeForm):
    ctype = CTypeChoiceField(label=_('Related resource'),
                             help_text=_('The proposed types of resource have '
                                         'at least a field which can be hidden.'
                                        ),
                             widget=DynamicSelect(attrs={'autocomplete': True}),
                            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        used_ct_ids = set(FieldsConfig.objects.values_list('content_type', flat=True))
        self.ctypes = ctypes = [ct for ct in map(ContentType.objects.get_for_model,
                                                 filter(FieldsConfig.is_model_valid, apps.get_models())
                                                )
                                        if ct.id not in used_ct_ids
                               ]

        if ctypes:
            self.fields['ctype'].ctypes = ctypes
        else:
            # TODO: remove the 'submit' button ?
            self.fields['ctype'] = CharField(
                    label=_('Related resource'),
                    required=False, widget=Label,
                    initial=_('All configurable types of resource are already configured.'),
                )

    def save(self):
        if self.ctypes:
            return FieldsConfig.objects.create(content_type=self.cleaned_data['ctype'],
                                               descriptions=(),
                                              )


class FieldsConfigEditForm(CremeModelForm):
    hidden = MultipleChoiceField(label=_('Hidden fields'), choices=(), required=False)

    class Meta(CremeModelForm.Meta):
        model = FieldsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        hidden_f = self.fields['hidden']
        hidden_f.choices = FieldsConfig.field_enumerator(instance.content_type.model_class()).choices()

        if instance.pk:
            hidden_f.initial = [f.name for f in instance.hidden_fields]

    def save(self, *args, **kwargs):
        # TODO: in clean for ValidationErrors ??
        HIDDEN = FieldsConfig.HIDDEN
        self.instance.descriptions = [(field_name, {HIDDEN: True})
                                        for field_name in self.cleaned_data['hidden']
                                     ]
        return super().save(*args, **kwargs)
