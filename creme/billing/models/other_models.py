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

from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeModel


#TODO: use a base abstract class ??


class InvoiceStatus(CremeModel):
    name = CharField(_(u'Status'), max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Invoice status')
        verbose_name_plural = _(u'Invoice status')


class QuoteStatus(CremeModel):
    name = CharField(_(u'Status'), max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Quote status')
        verbose_name_plural = _(u'Quote status')


class SalesOrderStatus(CremeModel):
    name = CharField(_(u'Status'), max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'billing'
        verbose_name = _(u'Salesorder status')
        verbose_name_plural = _(u'Salesorder status')
