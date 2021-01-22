# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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

import copy
import enum
import json

from django import forms
from django.forms.widgets import Select, Widget
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.widgets import ActionButtonList, DynamicSelect
from creme.creme_core.utils.unicode_collation import collator


# TODO: remove the 'Model' in name ?
# TODO: move to creme_core ?
class CreatorModelChoiceWidget(Select):
    template_name = 'creme_config/forms/widgets/creator-select.html'

    def __init__(
            self,
            creation_url='',
            creation_allowed=False,
            creation_label=_('Create'),
            *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed
        self.creation_label = creation_label

    def get_context(self, name, value, attrs):
        context = super().get_context(name=name, value=value, attrs=attrs)
        url = self.creation_url

        if url:
            final_attrs = context['widget']['attrs']

            if final_attrs is None or not ('disabled' in final_attrs or 'readonly' in final_attrs):
                button_list = ActionButtonList(
                    delegate=DynamicSelect(options=self.choices),
                    attrs=self.attrs,
                )

                allowed = self.creation_allowed
                label = str(self.creation_label)
                button_list.add_action(
                    'create', label,
                    icon='add', title=label if allowed else gettext('Cannot create'),
                    enabled=allowed, popupUrl=url,
                )

                context = button_list.get_context(name=name, value=value, attrs=attrs)

        return context


class ButtonMenuEditionWidget(Widget):
    template_name = 'creme_config/forms/widgets/buttonmenu-editor.html'

    def __init__(self, attrs=None, choices=()):
        super().__init__(attrs)
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices = [*choices]

    def create_option(self, name, button_id, button, selected):
        return {
            'name': name,
            'value': button_id,
            'label': str(button.verbose_name),
            'description': str(button.description),
            'selected': selected,
        }

    def create_options(self, name, value):
        """Return a list of optgroups for this widget."""
        options = []

        for button_id, button in self.choices:
            if button_id is None:
                button_id = ''
            selected = str(button_id) in value
            order = value.index(str(button_id)) + 1 if selected else 0
            options.append((order, button_id, button, selected))

        return [
            self.create_option(name, button_id, button, selected)
            for (order, button_id, button, selected)
            in sorted(options, key=lambda x: x[0])
        ]

    def value_from_datadict(self, data, files, name):
        return data.getlist(name)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['choices'] = self.create_options(name, context['widget']['value'])
        return context


class MenuEditionWidget(Widget):
    template_name = 'creme_config/forms/widgets/menu-editor.html'

    def __init__(self, attrs=None,
                 extra_entry_creators=(),
                 regular_entry_choices=()):
        super().__init__(attrs=attrs)
        self.extra_entry_creators = [*extra_entry_creators]
        self.regular_entry_choices = regular_entry_choices

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        widget = context['widget']
        widget['extra_creators'] = self.extra_entry_creators

        sort_key = collator.sort_key
        widget['regular_entry_choices'] = sorted(
            (
                (entry_id, str(entry_label))
                for entry_id, entry_label in self.regular_entry_choices
            ),
            key=lambda c: sort_key(c[1])
        )

        return context


class BricksConfigWidget(forms.Widget):
    template_name = "creme_config/forms/widgets/bricksconfig-editor.html"

    class zones(enum.Enum):
        TOP = "top"
        LEFT = "left"
        RIGHT = "right"
        BOTTOM = "bottom"

        @classmethod
        def values(cls):
            for location in cls:
                yield location.value

    def __init__(self, attrs=None, choices=()):
        super().__init__(attrs)
        self.choices = choices

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.attrs = self.attrs.copy()
        obj.choices = copy.copy(self.choices)
        memo[id(self)] = obj
        return obj

    def get_context(self, name, value, attrs):
        context = {}
        cleaned_value = self.clean_value(value)
        context['widget'] = {
            'name': name,
            'is_hidden': self.is_hidden,
            'required': self.is_required,
            'value': self.format_value(value),
            'attrs': self.build_attrs(self.attrs, attrs),
            'template_name': self.template_name,
            'choices': self.build_choices(name, cleaned_value, attrs),
        }
        return context

    def clean_value(self, value):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return

        if not isinstance(value, dict):
            return

        for zone in self.zones.values():
            if zone not in value:
                continue
            if not isinstance(value[zone], list):
                del value[zone]
        return value

    def build_choices(self, name, cleaned_value, attrs=None):
        choices = []
        for brick_id, brick in self.choices:
            brick_zone = None
            order = 0
            if cleaned_value:
                for zone in self.zones.values():
                    brick_ids = cleaned_value.get(zone)
                    if brick_ids is not None and brick_id in brick_ids:
                        brick_zone = zone
                        order = brick_ids.index(brick_id)
            choices.append({
                "value": brick_id,
                "orientation": brick_zone,
                "name": brick.verbose_name,
                "description": brick.description,
                "order": order
            })
        return [*sorted(choices, key=lambda choice: choice["order"])]

    def value_from_datadict(self, data, files, name):
        # Might not be in the data, or evaluated to False
        return data.get(name) or "{}"
