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

from django.forms.widgets import Select, Widget
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms.widgets import ActionButtonList, DynamicSelect


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
