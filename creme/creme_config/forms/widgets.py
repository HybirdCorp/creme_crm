# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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
from django.utils.translation import ugettext as _

from creme.creme_core.forms.widgets import ActionButtonList, DynamicSelect


class CreatorModelChoiceWidget(Select):
    def __init__(self, creation_url='', creation_allowed=False, *args, **kwargs):
        super(CreatorModelChoiceWidget, self).__init__(*args, **kwargs)
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed

    def render(self, name, value, attrs=None, choices=()):
        url = self.creation_url

        if not url:
            return super(CreatorModelChoiceWidget, self).render(name, value, attrs, choices)

        widget = ActionButtonList(delegate=DynamicSelect(options=self.choices),
                                  attrs=self.attrs,
                                 )

        allowed = self.creation_allowed
        widget.add_action('create', _(u'Add'), enabled=allowed, url=url,
                          title=_(u'Add') if allowed else _(u"Can't add"),
                         )

        return widget.render(name, value, attrs)  # TODO: choices ?
