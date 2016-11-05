# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2016  Hybird
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

from django.forms.fields import MultipleChoiceField, CharField
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.forms import CremeForm, CremeModelForm
from creme.creme_core.forms.fields import CTypeChoiceField
from creme.creme_core.forms.widgets import DynamicSelect, Label  # UnorderedMultipleChoiceWidget
from creme.creme_core.gui.fields_config import fields_config_registry
from creme.creme_core.models import FieldsConfig
from creme.creme_core.utils.meta import ModelFieldEnumerator


def _get_fields_enum(ctype):
    return ModelFieldEnumerator(ctype.model_class(), deep=0, only_leafs=False)\
                               .filter(viewable=True, optional=True)


class FieldsConfigAddForm(CremeForm):
    ctype = CTypeChoiceField(label=_(u'Related resource'),
                             help_text=_(u'The proposed types of resource have '
                                         u'at least a field which can be hidden.'
                                        ),
                             widget=DynamicSelect(attrs={'autocomplete': True}),
                            )

    def __init__(self, *args, **kwargs):
        super(FieldsConfigAddForm, self).__init__(*args, **kwargs)
        used_ct_ids = set(FieldsConfig.objects.values_list('content_type', flat=True))
        self.ctypes = ctypes = [ct for ct in fields_config_registry.ctypes
                                    if ct.id not in used_ct_ids and any(_get_fields_enum(ct))
                               ]

        if ctypes:
            self.fields['ctype'].ctypes = ctypes
        else:
            # TODO: remove the 'submit' button ?
            self.fields['ctype'] = CharField(
                    label=_(u'Related resource'),
                    required=False, widget=Label,
                    initial=_(u'All configurable types of resource are already configured.'),
                )

    def save(self):
        if self.ctypes:
            return FieldsConfig.objects.create(content_type=self.cleaned_data['ctype'],
                                               descriptions=(),
                                              )


class FieldsConfigEditForm(CremeModelForm):
    hidden = MultipleChoiceField(label=_(u'Hidden fields'), choices=(),
                                 # widget=UnorderedMultipleChoiceWidget,
                                 required=False,
                                )

    class Meta(CremeModelForm.Meta):
        model = FieldsConfig

    def __init__(self, *args, **kwargs):
        super(FieldsConfigEditForm, self).__init__(*args, **kwargs)
        instance = self.instance
        hidden_f = self.fields['hidden']
        hidden_f.choices = _get_fields_enum(instance.content_type).choices()

        if instance.pk:
            hidden_f.initial = [f.name for f in instance.hidden_fields]

    def save(self, *args, **kwargs):
        # TODO: in clean for ValidationErrors ??
        HIDDEN = FieldsConfig.HIDDEN
        self.instance.descriptions = [(field_name, {HIDDEN: True})
                                        for field_name in self.cleaned_data['hidden']
                                     ]
        return super(FieldsConfigEditForm, self).save(*args, **kwargs)
