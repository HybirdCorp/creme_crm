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

#from logging import debug

from django.forms import MultipleChoiceField, ChoiceField
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.forms import CremeForm
from creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme_core.gui.button_menu import button_registry
from creme_core.models import ButtonMenuItem
from creme_core.utils import creme_entity_content_types
from creme_core.utils.id_generator import generate_string_id_and_save


_PREFIX = 'creme_config-userbmi'


class ButtonMenuAddForm(CremeForm):
    ct_id = ChoiceField(label=_(u'Related resource'), choices=(), required=True,
                        help_text=_(u'The buttons related to this type of resource will be chosen by editing the configuration'),
                       )

    def __init__(self, *args, **kwargs):
        super(ButtonMenuAddForm, self).__init__(*args, **kwargs)

        entity_ct_ids = set(ct.id for ct in creme_entity_content_types())
        used_ct_ids   = set(ButtonMenuItem.objects.exclude(content_type=None)
                                                  .distinct()
                                                  .values_list('content_type_id', flat=True)
                           )
        self.fields['ct_id'].choices = [(ct.id, ct) for ct in ContentType.objects.filter(pk__in=entity_ct_ids - used_ct_ids)]

    def save(self):
        bmi = ButtonMenuItem(content_type_id=self.cleaned_data['ct_id'], button_id='', order=1)
        generate_string_id_and_save(ButtonMenuItem, [bmi], _PREFIX)


class ButtonMenuEditForm(CremeForm):
    button_ids = MultipleChoiceField(label=_(u'Buttons to display'), required=False,
                                    choices=(), widget=OrderedMultipleChoiceWidget)

    def __init__(self, button_menu_items, ct_id, *args, **kwargs):
        super(ButtonMenuEditForm, self).__init__(*args, **kwargs)

        self.ct = ContentType.objects.get_for_id(ct_id) if ct_id else None
        self.set_buttons = button_menu_items

        choices = []

        if not self.ct: #default conf
            choices.extend((id_, button.verbose_name) for id_, button in button_registry if not button.get_ctypes())
        else:
            model_class = self.ct.model_class()

            default_conf_ids = frozenset(ButtonMenuItem.objects.filter(content_type=None).values_list('button_id', flat=True))

            for id_, button in button_registry:
                ctypes = button.get_ctypes()

                if not ctypes:
                    if id_ not in default_conf_ids:
                        choices.append((id_, button.verbose_name))
                elif model_class in ctypes:
                    choices.append((id_, button.verbose_name))

        button_ids = self.fields['button_ids']
        button_ids.choices = choices
        button_ids.initial = [bmi.button_id for bmi in button_menu_items]

    def save(self):
        button_ids   = self.cleaned_data['button_ids']
        ct           = self.ct
        BMI_objects  = ButtonMenuItem.objects
        BMI_get      = BMI_objects.get
        items_2_save = []

        if not button_ids:
            BMI_objects.filter(content_type=ct).delete()  #No pk to BMI objects --> can delete() on queryset directly
            items_2_save.append(ButtonMenuItem(content_type=ct, button_id='', order=1)) #No button for this content type -> fake button_id
        else:
            old_ids = set(bmi.button_id for bmi in self.set_buttons)
            new_ids = set(button_ids)
            buttons_2_del = old_ids - new_ids
            buttons_2_add = new_ids - old_ids

            #No pk to BCI objects --> can delete() on queryset directly
            BMI_objects.filter(content_type=ct, button_id__in=buttons_2_del).delete()

            offset = 1 if ct is None else 1000 #default conf before ct's conf

            for i, button_id in enumerate(button_ids):
                if button_id in buttons_2_add:
                    items_2_save.append(ButtonMenuItem(content_type=ct, button_id=button_id, order=i + offset))
                else:
                    bmi = BMI_get(content_type=ct, button_id=button_id)

                    if bmi.order != i + offset:
                        bmi.order = i + offset
                        bmi.save()

        generate_string_id_and_save(ButtonMenuItem, items_2_save, _PREFIX)
