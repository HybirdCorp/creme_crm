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

from django.forms.widgets import Select
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.forms.widgets import ActionButtonList, DynamicSelect


class CreatorModelChoiceWidget(Select):
    template_name = 'creme_config/forms/widgets/creator-select.html'

    def __init__(self, creation_url='', creation_allowed=False, creation_label=_('Create'), *args, **kwargs):
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
                button_list = ActionButtonList(delegate=DynamicSelect(options=self.choices),
                                               attrs=self.attrs,
                                              )

                allowed = self.creation_allowed
                label = str(self.creation_label)
                button_list.add_action('create', label, enabled=allowed, popupUrl=url,
                                       title=label if allowed else ugettext(u'Cannot create'),
                                      )

                context = button_list.get_context(name=name, value=value, attrs=attrs)

        return context
