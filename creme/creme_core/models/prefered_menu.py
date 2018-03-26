# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.conf import settings
from django.db.models import Model, CharField, PositiveIntegerField, ForeignKey, CASCADE
from django.utils.translation import ugettext_lazy as _, ugettext


class PreferedMenuItem(Model):
    user  = ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_(u'User'), null=True, on_delete=CASCADE)
    label = CharField(_(u'Label'), max_length=100, blank=True)
    url   = CharField(_(u'Url'), max_length=100,  blank=True)
    order = PositiveIntegerField(_(u'Order'))

    class Meta:
        app_label = 'creme_core'

    @property
    def translated_label(self):
        from ..gui.menu import creme_menu

        url = self.url
        for app_item in creme_menu:
            for item in app_item.items:
                if item.url == url:
                    return unicode(item.name)

        # Fallback
        return ugettext(self.label)