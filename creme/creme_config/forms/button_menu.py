# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2022  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.forms import MultipleChoiceField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeForm
from creme.creme_core.forms.fields import EntityCTypeChoiceField
from creme.creme_core.forms.widgets import DynamicSelect
from creme.creme_core.gui import button_menu
from creme.creme_core.models import ButtonMenuItem
from creme.creme_core.utils.unicode_collation import collator

from .widgets import ButtonMenuEditionWidget


class ButtonMenuAddForm(CremeForm):
    ctype = EntityCTypeChoiceField(
        label=_('Related resource'),
        widget=DynamicSelect({'autocomplete': True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        used_ct_ids = {
            *ButtonMenuItem.objects.exclude(content_type=None)
                                   .distinct()
                                   .values_list('content_type_id', flat=True)
        }
        ct_field = self.fields['ctype']
        ct_field.ctypes = (ct for ct in ct_field.ctypes if ct.id not in used_ct_ids)

    # NB: never called
    def save(self, commit=True):
        bmi = ButtonMenuItem(content_type=self.cleaned_data['ctype'], button_id='', order=1)
        if commit:
            bmi.save()

        return bmi


class ButtonMenuEditForm(CremeForm):
    button_ids = MultipleChoiceField(
        label=_('Buttons to display'), required=False,
        choices=(), widget=ButtonMenuEditionWidget,
        help_text=_(
            'Drag and drop the buttons between the available buttons and '
            'the selected buttons sections to enable or disable the buttons, '
            'or within the selected buttons section to change the order.'
        ),
    )

    def __init__(self, button_menu_items, ct_id, button_registry=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ct = ContentType.objects.get_for_id(ct_id) if ct_id else None
        self.set_buttons = button_menu_items

        button_registry = button_registry or button_menu.button_registry
        choices = []

        if not self.ct:  # Default conf
            choices.extend(
                (id_, button)
                for id_, button in button_registry
                if not button.get_ctypes()
            )
        else:
            model_class = self.ct.model_class()

            default_conf_ids = frozenset(
                ButtonMenuItem.objects
                              .filter(content_type=None)
                              .values_list('button_id', flat=True)
            )

            for id_, button in button_registry:
                ctypes = button.get_ctypes()

                if not ctypes:
                    if id_ not in default_conf_ids:
                        choices.append((id_, button))
                elif model_class in ctypes:
                    choices.append((id_, button))

        sort_key = collator.sort_key
        choices.sort(key=lambda c: sort_key(str(c[1].verbose_name)))

        button_ids = self.fields['button_ids']
        button_ids.choices = choices
        button_ids.initial = [bmi.button_id for bmi in button_menu_items]

    def save(self):
        button_ids = self.cleaned_data['button_ids']
        ct = self.ct
        BMI_objects = ButtonMenuItem.objects
        BMI_get = BMI_objects.get

        if not button_ids:
            # No pk to BMI objects --> can delete() on queryset directly
            BMI_objects.filter(content_type=ct).delete()
            # No button for this content type -> fake button_id
            ButtonMenuItem.objects.create(content_type=ct, button_id='', order=1)
        else:
            old_ids = {bmi.button_id for bmi in self.set_buttons}
            new_ids = {*button_ids}
            buttons_2_del = old_ids - new_ids
            buttons_2_add = new_ids - old_ids

            # No pk to BCI objects --> can delete() on queryset directly
            BMI_objects.filter(content_type=ct, button_id__in=buttons_2_del).delete()

            offset = 1 if ct is None else 1000  # Default conf before ct's conf

            for i, button_id in enumerate(button_ids):
                if button_id in buttons_2_add:
                    ButtonMenuItem.objects.create(
                        content_type=ct, button_id=button_id, order=i + offset,
                    )
                else:
                    bmi = BMI_get(content_type=ct, button_id=button_id)

                    if bmi.order != i + offset:
                        bmi.order = i + offset
                        bmi.save()
