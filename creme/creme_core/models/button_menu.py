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

from django.db.models import CharField, ForeignKey, PositiveIntegerField
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import CremeModel


class ButtonMenuItem(CremeModel):
    id           = CharField(primary_key=True, max_length=100)
    content_type = ForeignKey(ContentType, verbose_name=_(u"Related type"), null=True)
    button_id    = CharField(_(u"Button ID"), max_length=100, blank=False, null=False)
    order        = PositiveIntegerField(_(u"Priority"))

    class Meta:
        app_label = 'creme_core'
        verbose_name = _(u'Button to display')
        verbose_name_plural = _(u'Buttons to display')
