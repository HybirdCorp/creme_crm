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

from django.db.models import Model, CharField, PositiveIntegerField, ForeignKey
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User


class PreferedMenuItem(Model):
    user  = ForeignKey(User, verbose_name=_(u'Utilisateur'), null=True)
    name  = CharField(_(u'Nom'), max_length=100, blank=True, null=True)
    label = CharField(_(u'Label'), max_length=100, blank=True, null=True)
    url   = CharField(_(u'Url'), max_length=100,  blank=True, null=True)
    order = PositiveIntegerField(_(u'Ordre'), blank=True, null=True)

    class Meta:
        app_label = 'creme_core'
