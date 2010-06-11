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

from django.db.models import ForeignKey
from django.utils.translation import ugettext_lazy as _

from products.models import Service

from line import Line


class ServiceLine(Line):
    related_item = ForeignKey(Service, verbose_name=_(u'Relatif au service'), blank=True, null=True) #related_name='service_line_set'

    def __unicode__(self):
        if self.related_item:
            return u"Related to service '%s'" % self.related_item
        return u"On the fly service '%s'" % self.on_the_fly_item

    def get_edit_form (self):
        from billing.forms.line import ServiceLineCreateForm, ServiceLineOnTheFlyCreateForm

        if self.related_item is not None:
            return ServiceLineCreateForm
        else:
            return ServiceLineOnTheFlyCreateForm

    def clone(self):
        sl = super(ServiceLine, self).clone()
        sl.related_item = self.related_item
        return sl

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Ligne service')
        verbose_name_plural = _(u'Lignes service')
